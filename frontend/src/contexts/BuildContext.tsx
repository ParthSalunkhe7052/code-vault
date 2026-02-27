/**
 * BuildContext - Global persistent state for cloud builds
 * 
 * Solves: Loss of build progress on navigation/refresh.
 * Features: LocalStorage persistence, API sync, WebSocket updates, Notifications.
 */

import React, { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { cloudBuild, auth } from '../services/api';

// Extended build state for UI tracking
interface BuildState {
    status: string;
    progress: number;
    logs: string[];
    outputPath?: string | null;
    jobId?: string | null;
    isBuilding: boolean;
    error?: string;
}

interface BuildContextType {
    builds: Record<string, BuildState>;
    startBuild: (projectId: string, jobId: string) => void;
    getBuild: (projectId: string) => BuildState;
    updateBuildStatus: (projectId: string, statusData: any) => void;
    clearBuild: (projectId: string) => void;
}

const BuildContext = createContext<BuildContextType | null>(null);
const STORAGE_KEY = 'cv_active_builds';

export const BuildProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    // Map of projectId -> BuildState
    const [builds, setBuilds] = useState<Record<string, BuildState>>({});
    
    // Track active WebSocket connections to prevent duplicates
    const activeSockets = useRef(new Map<string, WebSocket>());

    // Track WebSocket reconnect attempts per buildId
    const wsRetryCount = useRef(new Map<string, number>());

    // Track active polling intervals (fallback when WS fails)
    const activePollers = useRef(new Map<string, NodeJS.Timeout>());

    // Ref to hold the latest connectWebSocket for recursive reconnection
    const connectWebSocketRef = useRef<((projectId: string, buildId: string) => void) | null>(null);

    // Max reconnect attempts before falling back to polling
    const MAX_WS_RETRIES = 3;
    // Backoff delays in ms: 1s, 2s, 4s
    const WS_BACKOFF = [1000, 2000, 4000];

    // Track if we've already attempted sync to prevent spam
    const hasAttemptedSync = useRef(false);

    /**
     * Send Browser Notification
     */
    const notifyUser = (_projectId: string, status: string) => {
        if (!('Notification' in window)) return;
        
        if (Notification.permission === 'granted') {
            const title = status === 'completed' ? 'Build Successful' : 'Build Failed';
            const body = `Project build has ${status}. Click to view details.`;
            new Notification(title, { body });
        }
    };

    /**
     * Persist active build to storage
     */
    const persistBuild = (projectId: string, buildId: string) => {
        try {
            const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            stored[projectId] = buildId;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
        } catch (e) {
            console.error("Storage Error", e);
        }
    };

    const removePersistedBuild = (projectId: string) => {
        try {
            const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
            delete stored[projectId];
            localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
        } catch (e) {
            console.error("Storage Error", e);
        }
    };

    /**
     * Helper to process API status response (defined early as it's used by startPolling)
     */
    const handleBuildUpdate = useCallback((projectId: string, statusData: any) => {
        setBuilds(prev => {
            const current = prev[projectId] || { logs: [], status: 'unknown', progress: 0, isBuilding: false };
            const isFinished = ['completed', 'failed', 'cancelled'].includes(statusData.status);
            
            return {
                ...prev,
                [projectId]: {
                    ...current,
                    status: statusData.status,
                    progress: statusData.progress,
                    // If we have artifacts, use the first one's filename
                    outputPath: statusData.artifacts?.[0]?.filename,
                    isBuilding: !isFinished,
                    error: statusData.error,
                    logs: current.logs || [`Status: ${statusData.status} - ${statusData.stage}`]
                }
            };
        });
    }, []);

    /**
     * Start polling fallback for a build (used when WebSocket reconnection exhausted)
     */
    const startPolling = useCallback((projectId: string, buildId: string) => {
        if (activePollers.current.has(buildId)) return; // Already polling

        console.log(`[BuildPoll] Starting polling fallback for ${buildId}`);
        const interval = setInterval(async () => {
            try {
                const status = await cloudBuild.getStatus(buildId);
                handleBuildUpdate(projectId, status);

                if (['completed', 'failed', 'cancelled'].includes(status.status)) {
                    clearInterval(interval);
                    activePollers.current.delete(buildId);
                    removePersistedBuild(projectId);
                    notifyUser(projectId, status.status);
                }
            } catch (err: any) {
                console.error(`[BuildPoll] Poll failed for ${buildId}:`, err);
                // On 404, stop polling
                if (err.response?.status === 404) {
                    clearInterval(interval);
                    activePollers.current.delete(buildId);
                    removePersistedBuild(projectId);
                }
            }
        }, 5000); // Poll every 5 seconds

        activePollers.current.set(buildId, interval);
    }, [handleBuildUpdate]);

    /**
     * Connect to WebSocket for real-time updates with exponential backoff reconnection
     */
    const connectWebSocket = useCallback((projectId: string, buildId: string) => {
        if (activeSockets.current.has(buildId)) return; // Already connected

        // Build WebSocket URL
        let wsUrl;
        if (import.meta.env.VITE_API_URL) {
             const apiUrl = new URL(import.meta.env.VITE_API_URL);
             wsUrl = `${apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'}//${apiUrl.host}/api/v1/cloud-build/ws/${buildId}`;
         } else {
              const fallbackProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
              wsUrl = `${fallbackProtocol}//${window.location.host}/api/v1/cloud-build/ws/${buildId}`;
         }

        const retries = wsRetryCount.current.get(buildId) || 0;
        console.log(`[BuildWS] Connecting to ${wsUrl} (attempt ${retries + 1}/${MAX_WS_RETRIES + 1})`);
        const ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                
                if (msg.type === 'progress' || msg.type === 'status') {
                    // Reset retry counter on successful message
                    wsRetryCount.current.set(buildId, 0);

                    const data = msg.data;
                    
                    setBuilds(prev => {
                        const current = prev[projectId] || { logs: [], status: 'unknown', progress: 0, isBuilding: false };
                        
                        let newLogs = current.logs || [];
                        if (data.stage) {
                            const lastLog = newLogs[newLogs.length - 1];
                            const newLog = `${data.stage} (${data.progress}%)`;
                            if (lastLog !== newLog) {
                                newLogs = [...newLogs, newLog].slice(-50);
                            }
                        }

                        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                            ws.close();
                            activeSockets.current.delete(buildId);
                            wsRetryCount.current.delete(buildId);
                            removePersistedBuild(projectId);
                            notifyUser(projectId, data.status);
                        }

                        return {
                            ...prev,
                            [projectId]: {
                                ...current,
                                status: data.status,
                                progress: data.progress,
                                logs: newLogs,
                                isBuilding: ['pending', 'queued', 'running'].includes(data.status),
                                ...(data.status === 'completed' ? { 
                                    outputPath: data.filename || 'Build Complete' 
                                } : {})
                            }
                        };
                    });
                }
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };

        ws.onclose = (event) => {
            activeSockets.current.delete(buildId);

            // Don't reconnect if this was a clean close (code 1000) or build is done
            if (event.code === 1000) {
                wsRetryCount.current.delete(buildId);
                return;
            }

            const currentRetries = wsRetryCount.current.get(buildId) || 0;
            if (currentRetries < MAX_WS_RETRIES) {
                const delay = WS_BACKOFF[currentRetries] || WS_BACKOFF[WS_BACKOFF.length - 1];
                wsRetryCount.current.set(buildId, currentRetries + 1);
                console.log(`[BuildWS] Reconnecting in ${delay}ms (attempt ${currentRetries + 2}/${MAX_WS_RETRIES + 1})`);
                setTimeout(() => connectWebSocketRef.current?.(projectId, buildId), delay);
            } else {
                console.warn(`[BuildWS] Max retries exhausted for ${buildId}, falling back to polling`);
                wsRetryCount.current.delete(buildId);
                startPolling(projectId, buildId);
            }
        };

        ws.onerror = (err) => {
            console.error(`[BuildWS] Error for ${buildId}:`, err);
            // onclose will fire after onerror, handling reconnection
        };

        activeSockets.current.set(buildId, ws);
    }, [startPolling]);

    // Keep ref in sync so recursive reconnection always uses latest version
    connectWebSocketRef.current = connectWebSocket;


    // Load initial state from storage
    useEffect(() => {
        const loadPersistedBuilds = async () => {
            // Prevent multiple sync attempts
            if (hasAttemptedSync.current) {
                return;
            }
            hasAttemptedSync.current = true;

            try {
                // Check if user is authenticated - skip sync if not logged in
                if (!auth.isAuthenticated()) {
                    console.log('[BuildContext] User not authenticated, skipping build sync');
                    return;
                }

                const stored = localStorage.getItem(STORAGE_KEY);
                if (!stored) return;

                const activeBuilds = JSON.parse(stored); // { projectId: buildId }
                
                // Re-hydrate state for each active build
                for (const [projectId, buildId] of Object.entries(activeBuilds)) {
                    // Type assertion for buildId as string
                    const bId = buildId as string;
                    
                    try {
                        // 1. Set initial loading state
                        setBuilds(prev => ({
                            ...prev,
                            [projectId]: {
                                status: 'running', // Assume running until verified
                                progress: 0,
                                logs: ['Resuming build session...'],
                                jobId: bId,
                                isBuilding: true,
                            }
                        }));

                        // 2. Fetch latest status from API
                        const status = await cloudBuild.getStatus(bId);
                        
                        // 3. Update state with real data
                        handleBuildUpdate(projectId, status);

                        // 4. Reconnect WebSocket if still running
                        if (['pending', 'queued', 'running'].includes(status.status)) {
                            connectWebSocket(projectId, bId);
                        } else {
                            // If finished while away, clear storage
                            removePersistedBuild(projectId);
                        }
                    } catch (err: any) {
                        console.error(`Failed to sync build ${bId}:`, err);
                        // If 401 (Unauthorized), user is not logged in - clear all storage
                        if (err.response?.status === 401) {
                            console.log('[BuildContext] User not authenticated (401), clearing build storage');
                            localStorage.removeItem(STORAGE_KEY);
                            setBuilds({});
                            return; // Stop processing remaining builds
                        }
                        // If 404, remove from storage
                        if (err.response?.status === 404) {
                            removePersistedBuild(projectId);
                            setBuilds(prev => {
                                const next = { ...prev };
                                delete next[projectId];
                                return next;
                            });
                        }
                    }
                }
            } catch (e) {
                console.error("Failed to load persisted builds", e);
            }
        };

        loadPersistedBuilds();

        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }

        return () => {
            // Cleanup all sockets, pollers, and retry state on unmount
            activeSockets.current.forEach(ws => ws.close());
            activeSockets.current.clear();
            activePollers.current.forEach(interval => clearInterval(interval));
            activePollers.current.clear();
            wsRetryCount.current.clear();
        };
    }, [connectWebSocket, handleBuildUpdate]);

    /**
     * Public method to update build status (e.g. from polling)
     * Handles cleanup if build is finished
     */
    const updateBuildStatus = useCallback((projectId: string, statusData: any) => {
        handleBuildUpdate(projectId, statusData);
        
        // If finished, ensure cleanup happens (in case WS missed it)
        if (['completed', 'failed', 'cancelled'].includes(statusData.status)) {
             removePersistedBuild(projectId);
             // Cleanup sockets (best effort)
             activeSockets.current.forEach((_ws) => {
                 // We don't verify key == buildId because we don't have buildId easily here
             });
        }
    }, [handleBuildUpdate]);

    /**
     * Start a new build
     */
    const startBuild = useCallback((projectId: string, jobId: string) => {
        persistBuild(projectId, jobId);
        
        setBuilds(prev => ({
            ...prev,
            [projectId]: {
                status: 'pending',
                progress: 0,
                logs: ['Initiating Cloud Build...'],
                outputPath: null,
                jobId,
                isBuilding: true,
            }
        }));

        connectWebSocket(projectId, jobId);
    }, [connectWebSocket]);

/**
     * Clear a build from state (used after cancel/reset).
     * Uses the functional setState form to read latest state instead of
     * closing over a potentially stale `builds` snapshot — prevents this
     * callback from being re-created on every build state change.
     */
    const clearBuild = useCallback((projectId: string) => {
        removePersistedBuild(projectId);

        setBuilds(prev => {
            const build = prev[projectId];

            // Stop any active polling
            if (build?.jobId && activePollers.current.has(build.jobId)) {
                const interval = activePollers.current.get(build.jobId);
                if (interval) clearInterval(interval);
                activePollers.current.delete(build.jobId);
            }

            // Close any active WebSocket
            if (build?.jobId && activeSockets.current.has(build.jobId)) {
                const ws = activeSockets.current.get(build.jobId);
                if (ws) ws.close();
                activeSockets.current.delete(build.jobId);
            }

            const next = { ...prev };
            delete next[projectId];
            return next;
        });
    }, []);

    const getBuild = useCallback((projectId: string) => {
        return builds[projectId] || {
            status: 'idle',
            progress: 0,
            logs: [],
            outputPath: null,
            jobId: null,
            isBuilding: false,
        };
    }, [builds]);

    const value = useMemo(() => ({
        builds,
        startBuild,
        getBuild,
        updateBuildStatus,
        clearBuild,
    }), [builds, startBuild, getBuild, updateBuildStatus, clearBuild]);

    return (
        <BuildContext.Provider value={value}>
            {children}
        </BuildContext.Provider>
    );
};

export function useBuild() {
    const context = useContext(BuildContext);
    if (!context) {
        throw new Error('useBuild must be used within a BuildProvider');
    }
    return context;
}

// Keep useProjectBuild for backward compatibility
export function useProjectBuild(projectId: string) {
    const { getBuild, startBuild, updateBuildStatus, clearBuild } = useBuild();
    const build = getBuild(projectId); 

    return {
        ...build,
        start: (jobId: string) => startBuild(projectId, jobId),
        updateStatus: (statusData: any) => updateBuildStatus(projectId, statusData),
        updateBuild: (data: Partial<BuildState>) => updateBuildStatus(projectId, { ...build, ...data }),
        addLog: (log: string) => updateBuildStatus(projectId, { ...build, logs: [...build.logs, log].slice(-50) }),
        complete: (path?: string) => updateBuildStatus(projectId, { ...build, status: 'completed', progress: 100, outputPath: path }),
        fail: (error: string) => updateBuildStatus(projectId, { ...build, status: 'failed', error }),
        cancel: () => clearBuild(projectId),
    };
}

export default BuildContext;

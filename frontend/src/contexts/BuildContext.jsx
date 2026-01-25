/**
 * BuildContext - Global state for build progress persistence
 * 
 * Solves: Build progress lost when navigating between tabs
 * 
 * This context persists build state (status, progress, logs) globally,
 * so users can navigate away and return to see their ongoing build.
 */

import React, { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect } from 'react';

const BuildContext = createContext(null);

/**
 * Build state structure for each project
 * @typedef {Object} BuildState
 * @property {string} status - 'idle' | 'running' | 'completed' | 'failed' | 'cancelled'
 * @property {number} progress - 0-100
 * @property {string[]} logs - Build log messages
 * @property {string|null} outputPath - Path to output file when complete
 * @property {string|null} jobId - Backend job ID for cancellation
 * @property {boolean} isBuilding - Whether build is in progress
 */

export function BuildProvider({ children }) {
    // Map of projectId -> BuildState
    const [builds, setBuilds] = useState({});

    // Ref to track the currently active project ID for event listeners
    // We assume only one build runs at a time in the desktop app for now
    const activeProjectIdRef = useRef(null);

    /**
     * Start a new build for a project
     */
    const startBuild = useCallback((projectId, jobId = null) => {
        activeProjectIdRef.current = projectId; // Set active project for global listeners
        setBuilds(prev => ({
            ...prev,
            [projectId]: {
                status: 'running',
                progress: 0,
                logs: ['Starting build process...'],
                outputPath: null,
                jobId,
                isBuilding: true,
            }
        }));
    }, []);

    /**
     * Update build state for a project
     */
    const updateBuild = useCallback((projectId, updates) => {
        setBuilds(prev => {
            const current = prev[projectId] || {};
            return {
                ...prev,
                [projectId]: { ...current, ...updates }
            };
        });
    }, []);

    /**
     * Add a log message to a build
     */
    const addBuildLog = useCallback((projectId, message) => {
        setBuilds(prev => {
            const current = prev[projectId] || { logs: [] };
            return {
                ...prev,
                [projectId]: {
                    ...current,
                    logs: [...(current.logs || []).slice(-99), message]
                }
            };
        });
    }, []);

    /**
     * Global Event Listener for Tauri Compilation Events
     * This ensures updates continue even if the Wizard is closed.
     */
    useEffect(() => {
        // Only running in Tauri environment
        if (typeof window === 'undefined' || window.__TAURI__ === undefined) return;

        let unlistenProgress = null;
        let unlistenResult = null;

        const setupListeners = async () => {
            try {
                const { listen } = await import('@tauri-apps/api/event');

                // Listen for progress
                unlistenProgress = await listen('compilation-progress', (event) => {
                    const projectId = activeProjectIdRef.current;
                    if (!projectId) return;

                    const { progress: prog, message } = event.payload;

                    setBuilds(prev => {
                        const current = prev[projectId] || { logs: [] };
                        return {
                            ...prev,
                            [projectId]: {
                                ...current,
                                progress: prog,
                                logs: [...(current.logs || []).slice(-99), message]
                            }
                        };
                    });
                });

                // Listen for result
                unlistenResult = await listen('compilation-result', (event) => {
                    const projectId = activeProjectIdRef.current;
                    if (!projectId) return;

                    const { success, output_path, error_message } = event.payload;

                    setBuilds(prev => {
                        const current = prev[projectId] || {};
                        const updates = success ? {
                            status: 'completed',
                            progress: 100,
                            outputPath: output_path,
                            isBuilding: false,
                            logs: [...(current.logs || []), `✅ Build complete: ${output_path}`]
                        } : {
                            status: 'failed',
                            isBuilding: false,
                            logs: [...(current.logs || []), `❌ Build failed: ${error_message}`]
                        };

                        return {
                            ...prev,
                            [projectId]: { ...current, ...updates }
                        };
                    });

                    // Clear active project after result so we don't process stray events
                    // activeProjectIdRef.current = null; 
                    // Keeping it might be useful if late events come in, but strictly we should be done.
                });

            } catch (err) {
                console.error("Failed to setup global build listeners", err);
            }
        };

        setupListeners();

        return () => {
            if (unlistenProgress) unlistenProgress();
            if (unlistenResult) unlistenResult();
        };
    }, []);

    /**
     * Get build state for a project
     */
    const getBuild = useCallback((projectId) => {
        if (!projectId) {
            return {
                status: 'idle',
                progress: 0,
                logs: [],
                outputPath: null,
                jobId: null,
                isBuilding: false,
            };
        }
        return builds[projectId] || {
            status: 'idle',
            progress: 0,
            logs: [],
            outputPath: null,
            jobId: null,
            isBuilding: false,
        };
    }, [builds]);

    /**
     * Check if any build is running
     */
    const hasActiveBuilds = useCallback(() => {
        return Object.values(builds).some(b => b.status === 'running');
    }, [builds]);

    /**
     * Complete a build successfully
     */
    const completeBuild = useCallback((projectId, outputPath) => {
        setBuilds(prev => {
            const current = prev[projectId] || {};
            return {
                ...prev,
                [projectId]: {
                    ...current,
                    status: 'completed',
                    progress: 100,
                    outputPath,
                    isBuilding: false,
                    logs: [...(current.logs || []), `✅ Build complete: ${outputPath}`]
                }
            };
        });
    }, []);

    /**
     * Fail a build
     */
    const failBuild = useCallback((projectId, errorMessage) => {
        setBuilds(prev => {
            const current = prev[projectId] || {};
            return {
                ...prev,
                [projectId]: {
                    ...current,
                    status: 'failed',
                    isBuilding: false,
                    logs: [...(current.logs || []), `❌ Build failed: ${errorMessage}`]
                }
            };
        });
    }, []);

    /**
     * Cancel a build
     */
    const cancelBuild = useCallback((projectId) => {
        setBuilds(prev => {
            const current = prev[projectId] || {};
            return {
                ...prev,
                [projectId]: {
                    ...current,
                    status: 'cancelled',
                    isBuilding: false,
                    logs: [...(current.logs || []), '🛑 Build cancelled by user']
                }
            };
        });
    }, []);

    /**
     * Reset build state for a project
     */
    const resetBuild = useCallback((projectId) => {
        setBuilds(prev => {
            const newBuilds = { ...prev };
            delete newBuilds[projectId];
            return newBuilds;
        });
    }, []);

    const value = {
        builds,
        startBuild,
        updateBuild,
        addBuildLog,
        getBuild,
        hasActiveBuilds,
        completeBuild,
        failBuild,
        cancelBuild,
        resetBuild,
    };

    return (
        <BuildContext.Provider value={value}>
            {children}
        </BuildContext.Provider>
    );
}

/**
 * Hook to access build context
 */
export function useBuild() {
    const context = useContext(BuildContext);
    if (!context) {
        throw new Error('useBuild must be used within a BuildProvider');
    }
    return context;
}

/**
 * Hook for a specific project's build state
 * Memoized to prevent unnecessary re-renders
 */
export function useProjectBuild(projectId) {
    const { getBuild, updateBuild, addBuildLog, startBuild, completeBuild, failBuild, cancelBuild, builds } = useBuild();

    // Memoize the build retrieval to prevent new object creation on each render
    const build = useMemo(() => getBuild(projectId), [getBuild, projectId, builds]);

    // Memoize the callback functions to prevent new references on each render
    const memoizedUpdateBuild = useCallback(
        (updates) => updateBuild(projectId, updates),
        [updateBuild, projectId]
    );

    const memoizedAddLog = useCallback(
        (message) => addBuildLog(projectId, message),
        [addBuildLog, projectId]
    );

    const memoizedStart = useCallback(
        (jobId) => startBuild(projectId, jobId),
        [startBuild, projectId]
    );

    const memoizedComplete = useCallback(
        (outputPath) => completeBuild(projectId, outputPath),
        [completeBuild, projectId]
    );

    const memoizedFail = useCallback(
        (errorMessage) => failBuild(projectId, errorMessage),
        [failBuild, projectId]
    );

    const memoizedCancel = useCallback(
        () => cancelBuild(projectId),
        [cancelBuild, projectId]
    );

    // Memoize the entire return object to maintain stable reference
    return useMemo(() => ({
        ...build,
        updateBuild: memoizedUpdateBuild,
        addLog: memoizedAddLog,
        start: memoizedStart,
        complete: memoizedComplete,
        fail: memoizedFail,
        cancel: memoizedCancel,
    }), [build, memoizedUpdateBuild, memoizedAddLog, memoizedStart, memoizedComplete, memoizedFail, memoizedCancel]);
}

export default BuildContext;

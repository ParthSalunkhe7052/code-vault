/**
 * BuildContext - Global state for build progress persistence
 * 
 * Solves: Build progress lost when navigating between tabs
 * 
 * This context persists build state (status, progress, logs) globally,
 * so users can navigate away and return to see their ongoing build.
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

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

    /**
     * Start a new build for a project
     */
    const startBuild = useCallback((projectId, jobId = null) => {
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
 */
export function useProjectBuild(projectId) {
    const { getBuild, updateBuild, addBuildLog, startBuild, completeBuild, failBuild, cancelBuild } = useBuild();

    const build = getBuild(projectId);

    return {
        ...build,
        updateBuild: (updates) => updateBuild(projectId, updates),
        addLog: (message) => addBuildLog(projectId, message),
        start: (jobId) => startBuild(projectId, jobId),
        complete: (outputPath) => completeBuild(projectId, outputPath),
        fail: (errorMessage) => failBuild(projectId, errorMessage),
        cancel: () => cancelBuild(projectId),
    };
}

export default BuildContext;

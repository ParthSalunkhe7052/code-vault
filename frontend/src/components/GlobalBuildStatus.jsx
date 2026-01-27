import React from 'react';
import { useBuild } from '../contexts/BuildContext';
import { Loader2, CheckCircle, XCircle, X } from 'lucide-react';

const GlobalBuildStatus = () => {
    const { builds, updateBuild } = useBuild();

    // Find the most recent active or recently finished build
    // Prioritize running builds
    const activeBuild = Object.entries(builds).find(([_, b]) => ['pending', 'queued', 'running'].includes(b.status));
    
    // If no running build, check for recently finished/failed (that hasn't been dismissed)
    // We'll need a way to dismiss finished builds. For now, let's just show running ones.
    
    if (!activeBuild) return null;

    const [projectId, build] = activeBuild;

    // Helper to format stage
    const getStatusText = () => {
        if (build.status === 'running') return build.logs[build.logs.length - 1] || 'Building...';
        if (build.status === 'queued') return 'Queued...';
        return 'Initializing...';
    };

    return (
        <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5 fade-in duration-300">
            <div className="bg-[var(--cv-card)] border border-[var(--cv-border)] rounded-xl shadow-2xl p-4 w-80 backdrop-blur-xl">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                        <span className="font-bold text-sm text-[var(--cv-text)]">Cloud Build Active</span>
                    </div>
                    {/* <button className="text-[var(--cv-text-muted)] hover:text-[var(--cv-text)]">
                        <X size={16} />
                    </button> */}
                </div>

                <div className="space-y-3">
                    <div className="flex justify-between text-xs text-[var(--cv-text-muted)]">
                        <span className="truncate max-w-[180px]">{getStatusText()}</span>
                        <span>{build.progress}%</span>
                    </div>

                    <div className="h-1.5 w-full bg-[var(--cv-muted)] rounded-full overflow-hidden">
                        <div 
                            className="h-full bg-cyan-500 transition-all duration-500 ease-out"
                            style={{ width: `${build.progress}%` }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default GlobalBuildStatus;

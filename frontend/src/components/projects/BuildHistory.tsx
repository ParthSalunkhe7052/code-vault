import React, { useState, useEffect } from 'react';
import { History } from 'lucide-react';
import { cloudBuild } from '../../services/api';

interface Build {
    id: string;
    project_id: string;
    status: string;
    target_platforms?: string[];
    created_at: string;
}

interface BuildHistoryProps {
    projectId?: string;
    onRebuild?: (build: Build) => void;
}

const BuildHistory: React.FC<BuildHistoryProps> = ({ projectId, onRebuild }) => {
    const [builds, setBuilds] = useState<Build[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!projectId) {
            setLoading(false);
            return;
        }

        const fetchHistory = async () => {
            try {
                const data = await cloudBuild.getHistory(5);
                const projectBuilds = (data.builds as Build[])?.filter(b => b.project_id === projectId) || [];
                setBuilds(projectBuilds);
            } catch (error) {
                console.error('Failed to fetch build history:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, [projectId]);

    if (!projectId) {
        return null;
    }

    if (loading) {
        return (
            <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex items-center justify-center py-4">
                    <div className="rounded-full h-6 w-6 border-t-2 border-b-2 border-indigo-500 animate-spin" />
                </div>
            </div>
        );
    }

    if (builds.length === 0) {
        return null;
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'text-emerald-400';
            case 'running':
            case 'pending':
                return 'text-blue-400';
            case 'failed':
                return 'text-red-400';
            case 'cancelled':
                return 'text-slate-400';
            default:
                return 'text-slate-500';
        }
    };

    return (
        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h4 className="font-bold text-white mb-3 flex items-center gap-2">
                <History size={16} /> Recent Builds
            </h4>
            <div className="space-y-2">
                {builds.slice(0, 5).map(build => (
                    <div 
                        key={build.id} 
                        className="flex items-center justify-between p-2 bg-black/20 rounded-lg hover:bg-black/30 transition-colors"
                    >
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className={`text-xs font-bold uppercase ${getStatusColor(build.status)}`}>
                                    {build.status}
                                </span>
                                <span className="text-xs text-slate-500">
                                    {build.target_platforms?.join(', ') || 'windows'}
                                </span>
                            </div>
                            <span className="text-xs text-slate-600">
                                {new Date(build.created_at).toLocaleDateString()} {new Date(build.created_at).toLocaleTimeString()}
                            </span>
                        </div>
                        {build.status === 'completed' && onRebuild && (
                            <button 
                                onClick={() => onRebuild(build)}
                                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium px-2 py-1 rounded hover:bg-indigo-500/10 transition-colors"
                                title="Rebuild with same settings"
                            >
                                Rebuild →
                            </button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default BuildHistory;

import React from 'react';
import { Folder, MoreVertical, Edit, Trash2, Shield, Cpu, Activity, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { useProjectBuild } from '../../contexts/BuildContext';

const ProjectCard = ({
    project,
    index,
    activeDropdown,
    dropdownRef,
    onProjectClick,
    onDropdownToggle,
    onDelete
}) => {
    // Safety: Don't render if project is missing
    if (!project || !project.id) {
        return null;
    }

    // Get build state for this project
    const { status: buildStatus } = useProjectBuild(project.id);

    // Determine build status display
    const getBuildStatusDisplay = () => {
        switch (buildStatus) {
            case 'running':
            case 'pending':
                return {
                    text: 'Project wrapping under process...',
                    color: 'text-emerald-400',
                    bgColor: 'bg-emerald-500/10',
                    borderColor: 'border-emerald-500/20',
                    icon: <Loader2 size={12} className="animate-spin" />
                };
            case 'failed':
                return {
                    text: 'Build Failed',
                    color: 'text-red-400',
                    bgColor: 'bg-red-500/10',
                    borderColor: 'border-red-500/20',
                    icon: <XCircle size={12} />
                };
            case 'completed':
                return {
                    text: 'Build Ready',
                    color: 'text-emerald-400',
                    bgColor: 'bg-emerald-500/10',
                    borderColor: 'border-emerald-500/20',
                    icon: <CheckCircle size={12} />
                };
            default:
                return null;
        }
    };

    const buildStatusDisplay = getBuildStatusDisplay();

    return (
        <div
            onClick={() => onProjectClick(project)}
            className="glass-card p-6 group hover:border-indigo-500/50 transition-all duration-300 animate-fade-in relative overflow-visible cursor-pointer"
            style={{ animationDelay: `${index * 50}ms` }}
        >
            <div className="absolute top-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20">
                    <Activity size={10} />
                    <span>ACTIVE</span>
                </div>
            </div>

            <div className="flex items-start justify-between mb-6">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-indigo-500/20 text-blue-400 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-[0_0_15px_-5px_rgba(99,102,241,0.3)]">
                    <Folder size={24} />
                </div>
                <div className="relative">
                    <button
                        onClick={(e) => onDropdownToggle(e, project.id)}
                        className="text-slate-500 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/5"
                    >
                        <MoreVertical size={20} />
                    </button>

                    {activeDropdown === project.id && (
                        <ProjectDropdown
                            dropdownRef={dropdownRef}
                            onConfigure={() => onProjectClick(project)}
                            onDelete={() => onDelete(project.id)}
                        />
                    )}
                </div>
            </div>

            <h3 className="font-bold text-xl text-white mb-2 group-hover:text-indigo-400 transition-colors tracking-wide">
                {project.name}
            </h3>

            <p className="text-slate-400 text-sm mb-6 line-clamp-2 h-10 font-light">
                {project.description || 'No description provided.'}
            </p>

            <div className="pt-4 border-t border-white/5 flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-slate-500">
                    <Shield size={14} className="text-emerald-500/70" />
                    <span>{project.license_count} Licenses</span>
                </div>
                <div className="flex items-center gap-2">
                    {project.language === 'nodejs' ? (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-xs font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500"></span>
                            Node.js
                        </div>
                    ) : (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                            Python
                        </div>
                    )}
                </div>
            </div>

            {/* Build Status Indicator */}
            {buildStatusDisplay && (
                <div className={`mt-3 pt-3 border-t border-white/5 flex items-center gap-2 text-xs ${buildStatusDisplay.color}`}>
                    {buildStatusDisplay.icon}
                    <span>{buildStatusDisplay.text}</span>
                </div>
            )}

            {/* Hover Glow Effect */}
            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-500 -z-10" />
        </div>
    );
};

const ProjectDropdown = ({ dropdownRef, onConfigure, onDelete }) => (
    <div
        ref={dropdownRef}
        className="absolute right-0 top-full mt-2 w-48 bg-slate-900 border border-white/10 rounded-xl shadow-xl z-50 overflow-hidden animate-fade-in"
        onClick={(e) => e.stopPropagation()}
    >
        <button
            onClick={onConfigure}
            className="w-full px-4 py-3 text-left text-sm text-slate-300 hover:bg-white/5 hover:text-white flex items-center gap-2 transition-colors"
        >
            <Edit size={16} />
            Configure Project
        </button>
        <button
            onClick={onDelete}
            className="w-full px-4 py-3 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors"
        >
            <Trash2 size={16} />
            Delete Project
        </button>
    </div>
);

export default ProjectCard;


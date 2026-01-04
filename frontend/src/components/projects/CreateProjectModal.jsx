import React from 'react';
import Modal from '../Modal';
import { auth } from '../../services/api';

const CreateProjectModal = ({
    isOpen,
    onClose,
    newProject,
    setNewProject,
    onSubmit
}) => {
    const user = auth.getUser();
    const isFreeTier = !user || user.plan === 'free';

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Create New Project"
        >
            <form onSubmit={onSubmit} className="flex flex-col gap-4">
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Project Name
                    </label>
                    <input
                        type="text"
                        value={newProject.name}
                        onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                        className="input"
                        placeholder="e.g., Super App v1.0"
                        required
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Description
                    </label>
                    <textarea
                        value={newProject.description}
                        onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                        className="input min-h-[100px]"
                        placeholder="Brief description of your project..."
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Language
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            type="button"
                            onClick={() => setNewProject({ ...newProject, language: 'python' })}
                            className={`p-3 rounded-lg border border-slate-700 flex items-center justify-center gap-2 transition-all ${newProject.language !== 'nodejs'
                                ? 'bg-indigo-500/20 border-indigo-500 text-indigo-400'
                                : 'bg-slate-800/50 hover:bg-slate-800 text-slate-400'
                                }`}
                        >
                            <span className="font-medium">Python</span>
                        </button>

                        <div className="relative group">
                            <button
                                type="button"
                                disabled={isFreeTier}
                                onClick={() => !isFreeTier && setNewProject({ ...newProject, language: 'nodejs' })}
                                className={`w-full p-3 rounded-lg border border-slate-700 flex items-center justify-center gap-2 transition-all ${newProject.language === 'nodejs'
                                    ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                                    : isFreeTier
                                        ? 'bg-slate-800/30 text-slate-600 cursor-not-allowed opacity-60'
                                        : 'bg-slate-800/50 hover:bg-slate-800 text-slate-400'
                                    }`}
                            >
                                <span className="font-medium">Node.js</span>
                                {isFreeTier && <span className="text-xs bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded ml-1">PRO</span>}
                            </button>
                            {isFreeTier && (
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 text-xs text-slate-300 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none border border-slate-700">
                                    Upgrade to Pro for Node.js support
                                </div>
                            )}
                        </div>

                        {/* Coming Soon Languages */}
                        <button
                            type="button"
                            disabled
                            className="p-3 rounded-lg border border-slate-700/50 bg-slate-800/30 text-slate-600 cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            <span className="font-medium">Go</span>
                            <span className="text-xs bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Soon</span>
                        </button>

                        <button
                            type="button"
                            disabled
                            className="p-3 rounded-lg border border-slate-700/50 bg-slate-800/30 text-slate-600 cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            <span className="font-medium">C#</span>
                            <span className="text-xs bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">Soon</span>
                        </button>
                    </div>
                </div>

                <div className="flex justify-end gap-3 mt-4">
                    <button
                        type="button"
                        onClick={onClose}
                        className="btn btn-secondary"
                    >
                        Cancel
                    </button>
                    <button type="submit" className="btn btn-primary">
                        Create Project
                    </button>
                </div>
            </form>
        </Modal>
    );
};

export default CreateProjectModal;

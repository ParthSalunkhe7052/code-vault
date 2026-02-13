import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import Modal from '../Modal';
import { usePricing, TIERS } from '../../contexts/PricingContext';

const CreateProjectModal = ({
    isOpen,
    onClose,
    newProject,
    setNewProject,
    onSubmit,
    projectCount = 0
}) => {
    const { canCreateProject, tier } = usePricing();
    const canCreate = canCreateProject(projectCount);

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={canCreate ? "Create New Project" : "Project Limit Reached"}
        >
            {!canCreate ? (
                <div className="flex flex-col items-center text-center py-6">
                    <div className="p-4 rounded-full bg-violet-500/10 mb-4">
                        <Lock size={32} className="text-violet-400" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">Unlock Unlimited Projects</h3>
                    <p className="text-slate-400 mb-6">
                        You&apos;ve reached the limit of {projectCount} project(s) on the {tier} plan.
                        Upgrade to Pro to create unlimited projects.
                    </p>
                    <div className="flex gap-4 w-full">
                        <button
                            type="button"
                            onClick={onClose}
                            className="btn btn-secondary flex-1"
                        >
                            Cancel
                        </button>
                        <Link
                            to="/pricing"
                            onClick={onClose}
                            className="btn bg-gradient-to-r from-violet-600 to-indigo-600 text-white flex-1 justify-center"
                        >
                            Upgrade Now
                        </Link>
                    </div>
                </div>
            ) : (
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
                                    disabled={tier === TIERS.FREE}
                                    onClick={() => tier !== TIERS.FREE && setNewProject({ ...newProject, language: 'nodejs' })}
                                    className={`w-full p-3 rounded-lg border border-slate-700 flex items-center justify-center gap-2 transition-all ${newProject.language === 'nodejs'
                                        ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400'
                                        : tier === TIERS.FREE
                                            ? 'bg-slate-800/30 text-slate-600 cursor-not-allowed opacity-60'
                                            : 'bg-slate-800/50 hover:bg-slate-800 text-slate-400'
                                        }`}
                                >
                                    <span className="font-medium">Node.js</span>
                                    {tier === TIERS.FREE && <span className="text-xs bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded ml-1">PRO</span>}
                                </button>
                                {tier === TIERS.FREE && (
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-800 text-xs text-slate-300 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none border border-slate-700">
                                        Upgrade to Pro for Node.js support
                                    </div>
                                )}
                            </div>
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
            )}
        </Modal>
    );
};

export default CreateProjectModal;

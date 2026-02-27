import React from 'react';
import { Link } from 'react-router-dom';
import { Lock } from 'lucide-react';
import Modal from '../Modal';
import { usePricing } from '../../contexts/PricingContext';
import { Project, CreateLicenseRequest } from '../../types/api';

interface CreateLicenseModalProps {
    isOpen: boolean;
    onClose: () => void;
    projects: Project[];
    newLicense: CreateLicenseRequest;
    setNewLicense: (data: any) => void;
    featureInput: string;
    setFeatureInput: (value: string) => void;
    onSubmit: (e: React.FormEvent) => void;
    onAddFeature: () => void;
    onRemoveFeature: (feature: string) => void;
    licenseCount?: number;
}

const CreateLicenseModal: React.FC<CreateLicenseModalProps> = ({
    isOpen,
    onClose,
    projects,
    newLicense,
    setNewLicense,
    featureInput,
    setFeatureInput,
    onSubmit,
    onAddFeature,
    onRemoveFeature,
    licenseCount = 0
}) => {
    const { canCreateLicense, tier } = usePricing();
    const canCreate = canCreateLicense(licenseCount);

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={canCreate ? "Issue New License" : "License Limit Reached"}
        >
            {!canCreate ? (
                <div className="flex flex-col items-center text-center py-6">
                    <div className="p-4 rounded-full bg-violet-500/10 mb-4">
                        <Lock size={32} className="text-violet-400" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">Unlock Unlimited Licenses</h3>
                    <p className="text-slate-400 mb-6">
                        You&apos;ve reached the limit of {licenseCount} license(s) on the {tier} plan.
                        Upgrade to Pro to create more licenses.
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
                            Select Project
                        </label>
                        <select
                            value={newLicense.project_id}
                            onChange={(e) => setNewLicense({ ...newLicense, project_id: e.target.value })}
                            className="input"
                            required
                        >
                            <option value="" disabled>Choose a project...</option>
                            {projects.map(project => (
                                <option key={project.id} value={project.id}>
                                    {project.name}
                                </option>
                            ))}
                        </select>
                        {projects.length === 0 && (
                            <p className="text-xs text-amber-400 mt-1">
                                No projects found. Create a project first.
                            </p>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">
                                Client Name
                            </label>
                            <input
                                type="text"
                                value={newLicense.client_name || ''}
                                onChange={(e) => setNewLicense({ ...newLicense, client_name: e.target.value })}
                                className="input"
                                placeholder="Acme Corp"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">
                                Max Machines
                            </label>
                            <input
                                type="number"
                                min="1"
                                max="100"
                                value={newLicense.max_machines || 1}
                                onChange={(e) => setNewLicense({ ...newLicense, max_machines: parseInt(e.target.value) })}
                                className="input"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-2">
                            Client Email (Optional)
                        </label>
                        <input
                            type="email"
                            value={newLicense.client_email || ''}
                            onChange={(e) => setNewLicense({ ...newLicense, client_email: e.target.value })}
                            className="input"
                            placeholder="client@example.com"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-2">
                            Expiration Date
                        </label>
                        <input
                            type="datetime-local"
                            value={newLicense.expires_at || ''}
                            onChange={(e) => setNewLicense({ ...newLicense, expires_at: e.target.value })}
                            className="input"
                        />
                        <p className="text-xs text-slate-500 mt-1">Leave empty for a perpetual license</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-2">
                            Features / Modules
                        </label>
                        <div className="flex gap-2 mb-2">
                            <input
                                type="text"
                                value={featureInput}
                                onChange={(e) => setFeatureInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), onAddFeature())}
                                className="input"
                                placeholder="Add feature tag..."
                            />
                            <button
                                type="button"
                                onClick={onAddFeature}
                                className="btn btn-secondary"
                            >
                                Add
                            </button>
                        </div>
                        {(newLicense.features || []).length > 0 && (
                            <div className="flex flex-wrap gap-2 p-2 bg-slate-900/50 rounded-lg border border-slate-700/50">
                                {newLicense.features?.map((feature, i) => (
                                    <span key={i} className="flex items-center gap-1 px-2 py-1 bg-indigo-500/20 text-indigo-300 rounded text-xs">
                                        {feature}
                                        <button
                                            type="button"
                                            onClick={() => onRemoveFeature(feature)}
                                            className="hover:text-white"
                                        >
                                            ×
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                        <p className="text-xs text-slate-500 mt-1">
                            Features are passed to your application during license validation
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-2">
                            Notes (Internal)
                        </label>
                        <textarea
                            value={newLicense.notes || ''}
                            onChange={(e) => setNewLicense({ ...newLicense, notes: e.target.value })}
                            className="input min-h-[80px]"
                            placeholder="Internal notes about this license..."
                        />
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
                            Issue License
                        </button>
                    </div>
                </form>
            )}
        </Modal>
    );
};

export default CreateLicenseModal;
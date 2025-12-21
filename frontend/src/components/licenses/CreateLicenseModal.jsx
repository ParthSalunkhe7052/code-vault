import React, { useState } from 'react';
import { Calendar, Tag, X } from 'lucide-react';
import Modal from '../Modal';

const CreateLicenseModal = ({
    isOpen,
    onClose,
    onSubmit,
    projects,
    newLicense,
    setNewLicense,
    featureInput,
    setFeatureInput,
    onAddFeature,
    onRemoveFeature
}) => {
    const handleCreate = async (e) => {
        e.preventDefault();
        const licenseData = {
            ...newLicense,
            expires_at: newLicense.expires_at ? new Date(newLicense.expires_at).toISOString() : null
        };
        await onSubmit(e);
    };

    // Update project_id when projects change
    React.useEffect(() => {
        if (projects.length > 0 && !newLicense.project_id) {
            setNewLicense(prev => ({ ...prev, project_id: projects[0].id }));
        }
    }, [projects]);

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title="Issue New License"
        >
            <form onSubmit={handleCreate} className="flex flex-col gap-4">
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Project
                    </label>
                    <select
                        value={newLicense.project_id}
                        onChange={(e) => setNewLicense({ ...newLicense, project_id: e.target.value })}
                        className="input"
                        required
                    >
                        <option value="" disabled>Select a project</option>
                        {projects.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-400 mb-2">
                            Client Name
                        </label>
                        <input
                            type="text"
                            value={newLicense.client_name}
                            onChange={(e) => setNewLicense({ ...newLicense, client_name: e.target.value })}
                            className="input"
                            placeholder="John Doe"
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
                            value={newLicense.max_machines}
                            onChange={(e) => setNewLicense({ ...newLicense, max_machines: parseInt(e.target.value) })}
                            className="input"
                        />
                    </div>
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Client Email
                    </label>
                    <input
                        type="email"
                        value={newLicense.client_email}
                        onChange={(e) => setNewLicense({ ...newLicense, client_email: e.target.value })}
                        className="input"
                        placeholder="john@example.com"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        Expiration Date <span className="text-slate-500">(Optional)</span>
                    </label>
                    <div className="flex items-center gap-3">
                        <Calendar size={20} className="text-slate-400" />
                        <input
                            type="datetime-local"
                            value={newLicense.expires_at}
                            onChange={(e) => setNewLicense({ ...newLicense, expires_at: e.target.value })}
                            min={new Date().toISOString().slice(0, 16)}
                            className="input flex-1 w-auto"
                        />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Leave empty for a perpetual license</p>
                </div>

                {/* Features Input */}
                <div>
                    <label className="block text-sm font-medium text-slate-400 mb-2">
                        <div className="flex items-center gap-2">
                            <Tag size={14} />
                            Feature Flags
                        </div>
                    </label>
                    <div className="flex gap-2 mb-2">
                        <input
                            type="text"
                            value={featureInput}
                            onChange={(e) => setFeatureInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), onAddFeature())}
                            className="input flex-1"
                            placeholder="e.g., pro, enterprise, beta"
                        />
                        <button
                            type="button"
                            onClick={onAddFeature}
                            className="btn btn-secondary"
                        >
                            Add
                        </button>
                    </div>
                    {newLicense.features.length > 0 && (
                        <div className="flex flex-wrap gap-2 p-3 bg-slate-900/50 rounded-lg border border-white/10">
                            {newLicense.features.map((feature, i) => (
                                <span
                                    key={i}
                                    className="flex items-center gap-1 px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-sm"
                                >
                                    {feature}
                                    <button
                                        type="button"
                                        onClick={() => onRemoveFeature(feature)}
                                        className="hover:text-white ml-1"
                                    >
                                        <X size={12} />
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
                        Notes
                    </label>
                    <textarea
                        value={newLicense.notes}
                        onChange={(e) => setNewLicense({ ...newLicense, notes: e.target.value })}
                        className="input min-h-[80px]"
                        placeholder="Internal notes..."
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
        </Modal>
    );
};

export default CreateLicenseModal;

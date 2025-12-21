import React from 'react';
import Modal from '../Modal';

const WebhookFormModal = ({
    isOpen,
    onClose,
    title,
    formData,
    setFormData,
    availableEvents,
    onSubmit,
    submitLabel,
    isEdit = false
}) => {
    const toggleEvent = (event) => {
        setFormData(prev => ({
            ...prev,
            events: prev.events.includes(event)
                ? prev.events.filter(e => e !== event)
                : [...prev.events, event]
        }));
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={title}
        >
            <div className="space-y-4">
                <div>
                    <label className="block text-sm text-slate-400 mb-1">Name</label>
                    <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className="input w-full"
                        placeholder="My Webhook"
                    />
                </div>
                <div>
                    <label className="block text-sm text-slate-400 mb-1">URL</label>
                    <input
                        type="url"
                        value={formData.url}
                        onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                        className="input w-full"
                        placeholder="https://your-server.com/webhook"
                    />
                </div>
                <div>
                    <label className="block text-sm text-slate-400 mb-1">
                        {isEdit ? 'New Secret (leave empty to keep current)' : 'Secret (optional)'}
                    </label>
                    <input
                        type="text"
                        value={formData.secret}
                        onChange={(e) => setFormData({ ...formData, secret: e.target.value })}
                        className="input w-full"
                        placeholder={isEdit ? 'Enter new secret to change' : 'Used to sign webhook payloads'}
                    />
                    {!isEdit && (
                        <p className="text-xs text-slate-500 mt-1">If set, payloads will be signed with HMAC-SHA256</p>
                    )}
                </div>
                <div>
                    <label className="block text-sm text-slate-400 mb-2">Events</label>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {availableEvents.events.map(event => (
                            <label key={event} className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.events.includes(event)}
                                    onChange={() => toggleEvent(event)}
                                    className="form-checkbox rounded bg-slate-700 border-slate-600 text-primary"
                                />
                                <span className="text-white text-sm">{event}</span>
                            </label>
                        ))}
                    </div>
                </div>
                <div className="flex justify-end gap-3 pt-4">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onSubmit}
                        disabled={!formData.name || !formData.url || formData.events.length === 0}
                        className="btn-primary"
                    >
                        {submitLabel}
                    </button>
                </div>
            </div>
        </Modal>
    );
};

export default WebhookFormModal;

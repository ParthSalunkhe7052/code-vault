import React from 'react';
import { Webhook, Plus, CheckCircle2, AlertTriangle } from 'lucide-react';
import WebhookRow from './WebhookRow';

const WebhookTable = ({
    webhookList,
    onTest,
    onEdit,
    onViewDeliveries,
    onToggleActive,
    onDelete,
    onCreateClick
}) => {
    if (webhookList.length === 0) {
        return (
            <div className="glass-card overflow-hidden">
                <div className="p-8 text-center">
                    <Webhook className="mx-auto text-slate-600 mb-4" size={48} />
                    <h3 className="text-lg font-medium text-white mb-2">No webhooks configured</h3>
                    <p className="text-slate-400 mb-4">Create a webhook to receive notifications when events occur</p>
                    <button
                        onClick={onCreateClick}
                        className="btn-primary"
                    >
                        Create Your First Webhook
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card overflow-hidden">
            <table className="w-full">
                <thead className="bg-slate-800/50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">URL</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Events</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                    {webhookList.map(webhook => (
                        <WebhookRow
                            key={webhook.id}
                            webhook={webhook}
                            onTest={onTest}
                            onEdit={onEdit}
                            onViewDeliveries={onViewDeliveries}
                            onToggleActive={onToggleActive}
                            onDelete={onDelete}
                        />
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default WebhookTable;

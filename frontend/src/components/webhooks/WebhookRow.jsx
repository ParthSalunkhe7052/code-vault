import React from 'react';
import { Webhook, Trash2, Check, X, Edit2, Play, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';

const WebhookRow = ({
    webhook,
    onTest,
    onEdit,
    onViewDeliveries,
    onToggleActive,
    onDelete
}) => {
    return (
        <tr className="hover:bg-slate-800/30">
            <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                    <Webhook size={16} className="text-primary" />
                    <span className="text-white font-medium">{webhook.name}</span>
                </div>
            </td>
            <td className="px-6 py-4">
                <span className="text-slate-300 text-sm font-mono truncate block max-w-xs">
                    {webhook.url}
                </span>
            </td>
            <td className="px-6 py-4">
                <div className="flex flex-wrap gap-1">
                    {webhook.events.slice(0, 3).map(event => (
                        <span key={event} className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300">
                            {event.split('.')[1]}
                        </span>
                    ))}
                    {webhook.events.length > 3 && (
                        <span className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300">
                            +{webhook.events.length - 3}
                        </span>
                    )}
                </div>
            </td>
            <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                    {webhook.is_active ? (
                        <span className="flex items-center gap-1 text-green-400 text-sm">
                            <CheckCircle2 size={14} />
                            Active
                        </span>
                    ) : (
                        <span className="flex items-center gap-1 text-amber-400 text-sm">
                            <AlertTriangle size={14} />
                            Inactive
                        </span>
                    )}
                    {webhook.failure_count > 0 && (
                        <span className="text-red-400 text-xs">
                            ({webhook.failure_count} failures)
                        </span>
                    )}
                </div>
            </td>
            <td className="px-6 py-4 text-right">
                <div className="flex items-center justify-end gap-2">
                    <button
                        onClick={() => onTest(webhook.id)}
                        className="p-2 text-slate-400 hover:text-primary transition-colors"
                        title="Send test"
                    >
                        <Play size={16} />
                    </button>
                    <button
                        onClick={() => onViewDeliveries(webhook)}
                        className="p-2 text-slate-400 hover:text-primary transition-colors"
                        title="View deliveries"
                    >
                        <Clock size={16} />
                    </button>
                    <button
                        onClick={() => onEdit(webhook)}
                        className="p-2 text-slate-400 hover:text-primary transition-colors"
                        title="Edit"
                    >
                        <Edit2 size={16} />
                    </button>
                    <button
                        onClick={() => onToggleActive(webhook)}
                        className={`p-2 transition-colors ${webhook.is_active ? 'text-green-400 hover:text-red-400' : 'text-slate-400 hover:text-green-400'}`}
                        title={webhook.is_active ? 'Disable' : 'Enable'}
                    >
                        {webhook.is_active ? <X size={16} /> : <Check size={16} />}
                    </button>
                    <button
                        onClick={() => onDelete(webhook.id)}
                        className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                        title="Delete"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>
            </td>
        </tr>
    );
};

export default WebhookRow;

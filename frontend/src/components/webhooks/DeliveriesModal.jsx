import React from 'react';
import { CheckCircle2, X } from 'lucide-react';
import Modal from '../Modal';

const DeliveriesModal = ({
    isOpen,
    onClose,
    webhookName,
    deliveries
}) => {
    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Deliveries - ${webhookName}`}
        >
            <div className="space-y-4">
                {deliveries.length === 0 ? (
                    <p className="text-slate-400 text-center py-8">No deliveries yet</p>
                ) : (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {deliveries.map(delivery => (
                            <DeliveryItem key={delivery.id} delivery={delivery} />
                        ))}
                    </div>
                )}
                <div className="flex justify-end pt-4">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white"
                    >
                        Close
                    </button>
                </div>
            </div>
        </Modal>
    );
};

const DeliveryItem = ({ delivery }) => (
    <div
        className={`p-3 rounded-lg ${delivery.success ? 'bg-green-500/10 border border-green-500/20' : 'bg-red-500/10 border border-red-500/20'}`}
    >
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
                {delivery.success ? (
                    <CheckCircle2 size={16} className="text-green-400" />
                ) : (
                    <X size={16} className="text-red-400" />
                )}
                <span className="text-white text-sm font-medium">{delivery.event_type}</span>
            </div>
            <span className="text-slate-400 text-xs">
                {delivery.response_status && `HTTP ${delivery.response_status}`}
                {delivery.delivery_time_ms && ` • ${delivery.delivery_time_ms}ms`}
            </span>
        </div>
        <div className="text-slate-400 text-xs mt-1">
            {new Date(delivery.created_at).toLocaleString()}
        </div>
    </div>
);

export default DeliveriesModal;

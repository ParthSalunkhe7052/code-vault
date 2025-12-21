import React from 'react';
import { Monitor, Cpu, Globe, Clock, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import Modal from '../Modal';

const BindingsModal = ({
    isOpen,
    onClose,
    license,
    bindings,
    bindingsLoading,
    resetStatus,
    resetting,
    onResetHwid,
    onRemoveBinding
}) => {
    if (!license) return null;

    return (
        <Modal
            isOpen={isOpen}
            onClose={onClose}
            title={`Hardware Bindings: ${license.client_name || 'License'}`}
        >
            <div className="space-y-4">
                <div className="flex items-center justify-between text-sm text-slate-400 pb-2 border-b border-white/10">
                    <span>License: <span className="font-mono text-indigo-300">{license.license_key}</span></span>
                    <span>{license.active_machines}/{license.max_machines} machines</span>
                </div>
                
                {/* Reset Status Banner */}
                {resetStatus && resetStatus.reset_enabled && (
                    <ResetStatusBanner
                        resetStatus={resetStatus}
                        bindings={bindings}
                        resetting={resetting}
                        onResetHwid={onResetHwid}
                    />
                )}

                {bindingsLoading ? (
                    <LoadingSpinner />
                ) : bindings.length === 0 ? (
                    <EmptyBindings />
                ) : (
                    <BindingsList bindings={bindings} onRemoveBinding={onRemoveBinding} />
                )}

                <div className="flex justify-end pt-4 border-t border-white/10">
                    <button onClick={onClose} className="btn btn-secondary">
                        Close
                    </button>
                </div>
            </div>
        </Modal>
    );
};

const ResetStatusBanner = ({ resetStatus, bindings, resetting, onResetHwid }) => (
    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-white/10">
        <div className="text-sm">
            <span className="text-slate-400">HWID Resets: </span>
            <span className="text-white font-medium">
                {resetStatus.resets_remaining} / {resetStatus.monthly_limit}
            </span>
            <span className="text-slate-500 ml-1">remaining this month</span>
        </div>
        <button
            onClick={onResetHwid}
            disabled={resetting || resetStatus.resets_remaining <= 0 || bindings.length === 0}
            className="btn btn-secondary flex items-center gap-2 text-amber-400 hover:bg-amber-500/10 disabled:opacity-50 disabled:cursor-not-allowed"
        >
            <RefreshCw size={14} className={resetting ? 'animate-spin' : ''} />
            Reset All
        </button>
    </div>
);

const LoadingSpinner = () => (
    <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500"></div>
    </div>
);

const EmptyBindings = () => (
    <div className="text-center py-8 text-slate-500">
        <Monitor size={40} className="mx-auto mb-3 opacity-50" />
        <p>No machines bound to this license yet.</p>
    </div>
);

const BindingsList = ({ bindings, onRemoveBinding }) => (
    <div className="space-y-3 max-h-96 overflow-y-auto">
        {bindings.map((binding) => (
            <BindingCard key={binding.id} binding={binding} onRemove={onRemoveBinding} />
        ))}
    </div>
);

const BindingCard = ({ binding, onRemove }) => (
    <div className="bg-white/5 rounded-xl p-4 border border-white/10 hover:border-white/20 transition-colors">
        <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <Cpu size={20} />
                </div>
                <div>
                    <h4 className="font-medium text-white">
                        {binding.machine_name || 'Unknown Machine'}
                    </h4>
                    <p className="text-xs font-mono text-slate-500 mt-0.5">
                        HWID: {binding.hwid.substring(0, 16)}...
                    </p>
                </div>
            </div>
            <button
                onClick={() => onRemove(binding.id)}
                className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                title="Remove Binding"
            >
                <Trash2 size={16} />
            </button>
        </div>
        <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-2 gap-4 text-xs">
            <div className="flex items-center gap-2 text-slate-400">
                <Globe size={12} />
                <span>{binding.ip_address || 'Unknown IP'}</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
                <Clock size={12} />
                <span>Last seen: {new Date(binding.last_seen_at).toLocaleDateString()}</span>
            </div>
        </div>
        <div className="mt-2 flex items-center gap-2">
            {binding.is_active ? (
                <span className="flex items-center gap-1 text-xs text-emerald-400">
                    <CheckCircle size={10} /> Active
                </span>
            ) : (
                <span className="flex items-center gap-1 text-xs text-slate-500">
                    <XCircle size={10} /> Inactive
                </span>
            )}
        </div>
    </div>
);

export default BindingsModal;

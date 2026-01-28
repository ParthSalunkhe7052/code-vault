import React from 'react';
import { createPortal } from 'react-dom';
import { AlertTriangle } from 'lucide-react';

const ConfirmDialog = ({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    confirmVariant = 'danger'
}) => {
    const variants = {
        danger: 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/25',
        warning: 'bg-amber-500 hover:bg-amber-600 text-black shadow-lg shadow-amber-500/25',
        primary: 'bg-primary hover:bg-primary-dark text-white shadow-lg shadow-primary/25',
    };

    if (!isOpen) return null;

    const handleConfirm = () => {
        onConfirm();
        onClose();
    };

    return createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
            {/* Backdrop click to close */}
            <div className="absolute inset-0" onClick={onClose} />
            
            <div className="relative bg-gray-900/98 border border-white/15 rounded-2xl shadow-2xl shadow-black/50 p-6 max-w-sm w-full animate-scale-in">
                {/* Icon */}
                <div className="flex items-center gap-3 mb-4">
                    <div className={`p-2 rounded-xl ${
                        confirmVariant === 'danger' ? 'bg-red-500/20 text-red-400' :
                        confirmVariant === 'warning' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-primary/20 text-primary'
                    }`}>
                        <AlertTriangle size={20} />
                    </div>
                    <h3 className="text-lg font-bold text-white">{title}</h3>
                </div>
                
                <p className="text-slate-400 text-sm mb-6 pl-11">{message}</p>
                
                <div className="flex items-center justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg text-slate-400 hover:bg-white/10 
                            hover:text-white transition-colors font-medium"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={handleConfirm}
                        className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 
                            active:scale-95 ${variants[confirmVariant]}`}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>,
        document.body
    );
};

export default ConfirmDialog;

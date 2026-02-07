import React, { useEffect, useRef } from 'react';
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
    const dialogRef = useRef(null);
    const previousActiveElement = useRef(null);

    const variants = {
        danger: 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/25',
        warning: 'bg-amber-500 hover:bg-amber-600 text-black shadow-lg shadow-amber-500/25',
        primary: 'bg-primary hover:bg-primary-dark text-white shadow-lg shadow-primary/25',
    };

    // Focus management: save previous focus, auto-focus dialog, restore on close
    useEffect(() => {
        if (isOpen) {
            previousActiveElement.current = document.activeElement;

            // Focus the first focusable element (cancel button) after render
            setTimeout(() => {
                const focusable = dialogRef.current?.querySelector(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                focusable?.focus();
            }, 0);

            // Prevent body scroll
            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.body.style.overflow = '';
            if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
                previousActiveElement.current.focus();
            }
        };
    }, [isOpen]);

    // Keyboard handling: Escape to close, Tab trap
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (!isOpen) return;

            if (e.key === 'Escape') {
                e.preventDefault();
                onClose();
                return;
            }

            // Focus trap
            if (e.key === 'Tab') {
                const focusableElements = dialogRef.current?.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );

                if (!focusableElements || focusableElements.length === 0) return;

                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (e.shiftKey && document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                } else if (!e.shiftKey && document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const handleConfirm = () => {
        onConfirm();
        onClose();
    };

    return createPortal(
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-description"
        >
            {/* Backdrop click to close */}
            <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />
            
            <div
                ref={dialogRef}
                className="relative bg-gray-900/98 border border-white/15 rounded-2xl shadow-2xl shadow-black/50 p-6 max-w-sm w-full animate-scale-in"
            >
                {/* Icon + Title */}
                <div className="flex items-center gap-3 mb-4">
                    <div className={`p-2 rounded-xl ${
                        confirmVariant === 'danger' ? 'bg-red-500/20 text-red-400' :
                        confirmVariant === 'warning' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-primary/20 text-primary'
                    }`}>
                        <AlertTriangle size={20} aria-hidden="true" />
                    </div>
                    <h3 id="confirm-dialog-title" className="text-lg font-bold text-white">{title}</h3>
                </div>
                
                <p id="confirm-dialog-description" className="text-slate-400 text-sm mb-6 pl-11">{message}</p>
                
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

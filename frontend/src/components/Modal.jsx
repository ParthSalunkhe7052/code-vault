import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Modal Component with Accessibility Features
 * - Focus trap (Tab cycles within modal)
 * - Escape key closes modal
 * - Restores focus on close
 * - ARIA attributes for screen readers
 * - Prevents body scroll when open
 */
const Modal = ({ isOpen, onClose, title, children, size = 'md' }) => {
    const modalRef = useRef(null);
    const previousActiveElement = useRef(null);

    const sizes = {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-2xl',
        xl: 'max-w-4xl',
        full: 'max-w-6xl',
    };

    // Handle focus management and body scroll lock
    useEffect(() => {
        if (isOpen) {
            // Store currently focused element to restore later
            previousActiveElement.current = document.activeElement;

            // Focus first focusable element in modal
            setTimeout(() => {
                const focusable = modalRef.current?.querySelector(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                focusable?.focus();
            }, 0);

            // Prevent body scroll
            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.body.style.overflow = '';
            // Restore focus to previously focused element
            if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
                previousActiveElement.current.focus();
            }
        };
    }, [isOpen]);

    // Handle keyboard events (Escape to close, Tab trap)
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (!isOpen) return;

            // Close on Escape
            if (e.key === 'Escape') {
                e.preventDefault();
                onClose();
                return;
            }

            // Focus trap - keep Tab within modal
            if (e.key === 'Tab') {
                const focusableElements = modalRef.current?.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );

                if (!focusableElements || focusableElements.length === 0) return;

                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                // Shift+Tab on first element -> go to last
                if (e.shiftKey && document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
                // Tab on last element -> go to first
                else if (!e.shiftKey && document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4
                        bg-black/70 backdrop-blur-md"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="modal-title"
                >
                    {/* Click outside to close */}
                    <motion.div
                        className="absolute inset-0"
                        onClick={onClose}
                        aria-hidden="true"
                    />

                    <motion.div
                        ref={modalRef}
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ 
                            duration: 0.3, 
                            ease: [0.4, 0, 0.2, 1]
                        }}
                        className={`
                            relative ${sizes[size]} w-full
                            rounded-2xl shadow-2xl shadow-black/50 overflow-hidden
                            flex flex-col max-h-[85vh]
                        `}
                        style={{
                            backgroundColor: 'var(--cv-card-solid)',
                            border: '1px solid var(--cv-border)'
                        }}
                    >
                        {/* Header with gradient */}
                        <div
                            className="flex items-center justify-between p-5 shrink-0"
                            style={{
                                borderBottom: '1px solid var(--cv-border)',
                                background: 'linear-gradient(to right, var(--cv-border-subtle), transparent)'
                            }}
                        >
                            <h3 id="modal-title" className="font-bold text-lg" style={{ color: 'var(--cv-text)' }}>
                                {title}
                            </h3>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 hover:opacity-70"
                                style={{
                                    color: 'var(--cv-text-muted)',
                                    '--tw-ring-color': 'var(--cv-accent, currentColor)',
                                }}
                                aria-label="Close modal"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto custom-scrollbar">
                            {children}
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>,
        document.body
    );
};

export default Modal;

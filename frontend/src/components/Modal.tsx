import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
    size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

/**
 * Modal Component with Accessibility Features
 */
const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, size = 'md' }) => {
    const modalRef = useRef<HTMLDivElement>(null);
    const previousActiveElement = useRef<HTMLElement | null>(null);

    const sizes = {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-2xl',
        xl: 'max-w-4xl',
        full: 'max-w-6xl',
    };

    useEffect(() => {
        if (isOpen) {
            previousActiveElement.current = document.activeElement as HTMLElement;

            setTimeout(() => {
                const focusable = modalRef.current?.querySelector<HTMLElement>(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                focusable?.focus();
            }, 0);

            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.body.style.overflow = '';
            if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
                previousActiveElement.current.focus();
            }
        };
    }, [isOpen]);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (!isOpen) return;

            if (e.key === 'Escape') {
                e.preventDefault();
                onClose();
                return;
            }

            if (e.key === 'Tab') {
                const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );

                if (!focusableElements || focusableElements.length === 0) return;

                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (e.shiftKey && document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement?.focus();
                } else if (!e.shiftKey && document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement?.focus();
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return createPortal(
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4
                bg-black/70 backdrop-blur-md transition-opacity duration-200"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
        >
            <div
                className="absolute inset-0"
                onClick={onClose}
                aria-hidden="true"
            />

            <div
                ref={modalRef}
                className={`
                    relative ${sizes[size]} w-full
                    rounded-2xl shadow-2xl shadow-black/50 overflow-hidden
                    flex flex-col max-h-[85vh]
                    transition-all duration-200
                `}
                style={{
                    backgroundColor: 'var(--cv-card-solid)',
                    border: '1px solid var(--cv-border)'
                } as React.CSSProperties}
            >
                <div
                    className="flex items-center justify-between p-5 shrink-0"
                    style={{
                        borderBottom: '1px solid var(--cv-border)',
                        background: 'linear-gradient(to right, var(--cv-border-subtle), transparent)'
                    } as React.CSSProperties}
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
                        } as React.CSSProperties}
                        aria-label="Close modal"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="p-6 overflow-y-auto custom-scrollbar">
                    {children}
                </div>
            </div>
        </div>,
        document.body
    );
};

export default Modal;

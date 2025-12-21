import React from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

const Modal = ({ isOpen, onClose, title, children, size = 'md' }) => {
    const sizes = {
        sm: 'max-w-sm',
        md: 'max-w-md',
        lg: 'max-w-2xl',
        xl: 'max-w-4xl',
        full: 'max-w-6xl',
    };

    if (!isOpen) return null;

    return createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 
            bg-black/70 backdrop-blur-md animate-fade-in">
            
            {/* Click outside to close */}
            <div className="absolute inset-0" onClick={onClose} />
            
            <div className={`
                relative ${sizes[size]} w-full bg-gray-900/98 border border-white/15 
                rounded-2xl shadow-2xl shadow-black/50 overflow-hidden 
                transform transition-all animate-scale-in
                flex flex-col max-h-[85vh]
            `}>
                {/* Header with gradient */}
                <div className="flex items-center justify-between p-5 
                    border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent shrink-0">
                    <h3 className="font-bold text-lg text-white">{title}</h3>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-white/10 text-slate-400 
                            hover:text-white transition-all"
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

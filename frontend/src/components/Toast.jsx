import React, { useEffect, useState, createContext, useContext, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

// Toast Context
const ToastContext = createContext(null);

// Toast Provider Component
export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info', duration = 4000) => {
        const id = Date.now() + Math.random();
        setToasts(prev => [...prev, { id, message, type, duration }]);
        return id;
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    }, []);

    const toast = {
        success: (message, duration) => addToast(message, 'success', duration),
        error: (message, duration) => addToast(message, 'error', duration),
        warning: (message, duration) => addToast(message, 'warning', duration),
        info: (message, duration) => addToast(message, 'info', duration),
    };

    return (
        <ToastContext.Provider value={toast}>
            {children}
            <ToastContainer toasts={toasts} onRemove={removeToast} />
        </ToastContext.Provider>
    );
};

// Hook to use toast
export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};

// Toast Container
const ToastContainer = ({ toasts, onRemove }) => {
    if (toasts.length === 0) return null;

    return createPortal(
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm">
            {toasts.map(toast => (
                <ToastItem key={toast.id} {...toast} onClose={() => onRemove(toast.id)} />
            ))}
        </div>,
        document.body
    );
};

// Individual Toast Item
const ToastItem = ({ message, type = 'info', duration = 4000, onClose }) => {
    const [isExiting, setIsExiting] = useState(false);

    const icons = {
        success: CheckCircle,
        error: XCircle,
        warning: AlertTriangle,
        info: Info,
    };

    const styles = {
        success: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
        error: 'bg-red-500/15 border-red-500/30 text-red-400',
        warning: 'bg-amber-500/15 border-amber-500/30 text-amber-400',
        info: 'bg-blue-500/15 border-blue-500/30 text-blue-400',
    };

    const iconStyles = {
        success: 'text-emerald-400',
        error: 'text-red-400',
        warning: 'text-amber-400',
        info: 'text-blue-400',
    };

    const Icon = icons[type];

    useEffect(() => {
        if (duration > 0) {
            const timer = setTimeout(() => {
                setIsExiting(true);
                setTimeout(onClose, 200);
            }, duration);
            return () => clearTimeout(timer);
        }
    }, [duration, onClose]);

    const handleClose = () => {
        setIsExiting(true);
        setTimeout(onClose, 200);
    };

    return (
        <div
            className={`
                flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl 
                shadow-lg shadow-black/20 min-w-[280px]
                transition-all duration-200
                ${styles[type]}
                ${isExiting ? 'opacity-0 translate-x-4' : 'animate-slide-up'}
            `}
        >
            <Icon size={18} className={iconStyles[type]} />
            <span className="text-sm font-medium flex-1 text-white">{message}</span>
            <button
                onClick={handleClose}
                className="p-1 hover:bg-white/10 rounded-lg transition-colors"
            >
                <X size={14} className="text-slate-400 hover:text-white" />
            </button>
        </div>
    );
};

export default ToastItem;

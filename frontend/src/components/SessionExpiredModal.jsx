
import { createPortal } from 'react-dom';
import { LogOut, AlertTriangle } from 'lucide-react';

/**
 * SessionExpiredModal - Shown when a 401 response is received.
 * Gives the user a chance to acknowledge before redirecting to login.
 * Prevents data loss from mid-form hard navigation.
 */
const SessionExpiredModal = ({ onAcknowledge }) => {
    return createPortal(
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="session-expired-title"
            aria-describedby="session-expired-description"
        >
            <div className="relative bg-gray-900 border border-white/15 rounded-2xl shadow-2xl shadow-black/50 p-8 max-w-sm w-full animate-scale-in text-center">
                <div className="flex justify-center mb-4">
                    <div className="p-3 rounded-xl bg-amber-500/20">
                        <AlertTriangle size={28} className="text-amber-400" aria-hidden="true" />
                    </div>
                </div>

                <h3 id="session-expired-title" className="text-xl font-bold text-white mb-2">
                    Session Expired
                </h3>
                <p id="session-expired-description" className="text-slate-400 text-sm mb-6">
                    Your session has expired. Please log in again to continue. Any unsaved work on this page may still be recoverable -- copy important data before proceeding.
                </p>

                <button
                    onClick={onAcknowledge}
                    autoFocus
                    className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-bold text-sm uppercase tracking-wide bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg hover:shadow-indigo-500/25 transition-all"
                >
                    <LogOut size={16} aria-hidden="true" />
                    Go to Login
                </button>
            </div>
        </div>,
        document.body
    );
};

export default SessionExpiredModal;

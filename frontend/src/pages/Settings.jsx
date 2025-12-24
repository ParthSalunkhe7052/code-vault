import { useState, useEffect } from 'react';
import { Key, RefreshCw, Copy, Check, User, Mail, Lock, Eye, EyeOff } from 'lucide-react';
import { auth } from '../services/api';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const Settings = () => {
    const toast = useToast();
    const [user, setUser] = useState(null);
    const [apiKey, setApiKey] = useState('');
    const [loading, setLoading] = useState(true);
    const [regenerating, setRegenerating] = useState(false);
    const [copied, setCopied] = useState(false);
    const [showKey, setShowKey] = useState(false);
    const [confirmDialog, setConfirmDialog] = useState({
        isOpen: false,
        onConfirm: () => { }
    });

    useEffect(() => {
        loadUser();
    }, []);

    const loadUser = async () => {
        try {
            const userData = await auth.getMe();
            setUser(userData);
            setApiKey(userData.api_key || '');
        } catch (error) {
            console.error('Failed to load user:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleRegenerateKey = async () => {
        setConfirmDialog({
            isOpen: true,
            onConfirm: async () => {
                setRegenerating(true);
                try {
                    const result = await auth.regenerateApiKey();
                    setApiKey(result.api_key);
                    toast.success('API key regenerated successfully');
                } catch (error) {
                    console.error('Failed to regenerate API key:', error);
                    toast.error('Failed to regenerate API key');
                } finally {
                    setRegenerating(false);
                }
            }
        });
    };

    const handleCopyKey = async () => {
        try {
            await navigator.clipboard.writeText(apiKey);
            setCopied(true);
            toast.success('API key copied to clipboard');
            setTimeout(() => setCopied(false), 2000);
        } catch (error) {
            console.error('Failed to copy:', error);
            toast.error('Failed to copy to clipboard');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <RefreshCw className="animate-spin text-primary" size={32} />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-white">Settings</h1>
                <p className="text-slate-400 mt-1">Manage your account and API access</p>
            </div>

            {/* User Info */}
            <div className="glass-card p-6">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <User size={20} className="text-primary" />
                    Account Information
                </h2>

                <div className="grid gap-4 md:grid-cols-2">
                    <div>
                        <label className="text-sm text-slate-400">Email</label>
                        <div className="flex items-center gap-2 mt-1">
                            <Mail size={16} className="text-slate-500" />
                            <span className="text-white">{user?.email}</span>
                        </div>
                    </div>
                    <div>
                        <label className="text-sm text-slate-400">Name</label>
                        <p className="text-white mt-1">{user?.name || 'Not set'}</p>
                    </div>
                    <div>
                        <label className="text-sm text-slate-400">Plan</label>
                        <p className="text-white mt-1 capitalize">{user?.plan || 'free'}</p>
                    </div>
                </div>
            </div>

            {/* API Key Section */}
            <div className="glass-card p-6 relative overflow-hidden">
                {/* Decorative element */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full 
                    blur-3xl -translate-y-1/2 translate-x-1/2" />

                <div className="relative">
                    <h2 className="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                        <Key size={20} className="text-primary" />
                        API Key
                        <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded-full ml-2">
                            Secret
                        </span>
                    </h2>

                    <p className="text-slate-400 text-sm mb-4">
                        Use this API key to authenticate requests from your protected applications.
                        Keep it secret and never expose it in client-side code.
                    </p>

                    {/* Enhanced API key display */}
                    <div className="flex items-center gap-3 p-4 bg-gray-950/50 rounded-xl border border-white/10">
                        <Lock size={16} className="text-slate-500" />
                        <input
                            type={showKey ? 'text' : 'password'}
                            value={apiKey}
                            readOnly
                            className="flex-1 bg-transparent border-none font-mono text-sm 
                                text-slate-300 focus:outline-none tracking-wider"
                        />
                        <button
                            onClick={() => setShowKey(!showKey)}
                            className="p-2 rounded-lg hover:bg-white/10 text-slate-400 
                                hover:text-white transition-colors"
                            title={showKey ? 'Hide key' : 'Show key'}
                        >
                            {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                        <button
                            onClick={handleCopyKey}
                            className="p-2 rounded-lg hover:bg-white/10 text-slate-400 
                                hover:text-white transition-colors"
                            title="Copy key"
                        >
                            {copied ? (
                                <Check size={16} className="text-emerald-400" />
                            ) : (
                                <Copy size={16} />
                            )}
                        </button>
                    </div>

                    <div className="flex items-center gap-3 mt-4">
                        <button
                            onClick={handleRegenerateKey}
                            disabled={regenerating}
                            className="btn-primary flex items-center gap-2"
                        >
                            <RefreshCw size={16} className={regenerating ? 'animate-spin' : ''} />
                            Regenerate Key
                        </button>
                    </div>
                </div>

                <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <p className="text-amber-400 text-sm">
                        ⚠️ Regenerating your API key will invalidate the current key immediately.
                        Any applications using the old key will stop working.
                    </p>
                </div>
            </div>

            {/* Usage Example */}
            <div className="glass-card p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Usage Example</h2>

                <p className="text-slate-400 text-sm mb-3">
                    Include your API key in the X-API-Key header when making requests:
                </p>

                <pre className="bg-slate-900/50 rounded-lg p-4 overflow-x-auto">
                    <code className="text-sm text-slate-300">
                        {`curl -X POST https://your-server.com/api/v1/license/validate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${apiKey || 'your-api-key'}" \\
  -d '{"license_key": "...", "hwid": "..."}'`}
                    </code>
                </pre>
            </div>

            {/* Confirm Dialog */}
            <ConfirmDialog
                isOpen={confirmDialog.isOpen}
                onClose={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
                onConfirm={confirmDialog.onConfirm}
                title="Regenerate API Key"
                message="Are you sure? This will invalidate your current API key. Any applications using the old key will stop working."
                confirmText="Regenerate"
                confirmVariant="warning"
            />
        </div>
    );
};

export default Settings;

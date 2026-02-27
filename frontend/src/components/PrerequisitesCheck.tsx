import React, { useState, useEffect, useCallback } from 'react';
import { CheckCircle, XCircle, Loader2, Download, AlertTriangle, ExternalLink } from 'lucide-react';

interface ToolStatus {
    loading: boolean;
    installed: boolean;
    version: string | null;
    path?: string | null;
}

interface PrerequisitesCheckProps {
    isOpen: boolean;
    onReady: () => void;
    onDismiss: () => void;
    language?: 'python' | 'nodejs' | undefined;
}

/**
 * PrerequisitesCheck - Modal component to verify build requirements
 */
const PrerequisitesCheck: React.FC<PrerequisitesCheckProps> = ({ isOpen, onReady, onDismiss, language = 'python' }) => {
    const isNodeJS = language === 'nodejs';

    const [status, setStatus] = useState({
        runtime: { loading: true, installed: false, version: null, path: null } as ToolStatus,
        compiler: { loading: true, installed: false, version: null } as ToolStatus,
        nsis: { loading: true, installed: false, version: null } as ToolStatus
    });
    const [installing, setInstalling] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const checkAll = useCallback(async () => {
        setStatus({
            runtime: { loading: true, installed: false, version: null, path: null },
            compiler: { loading: true, installed: false, version: null },
            nsis: { loading: true, installed: false, version: null }
        });
        setError(null);

        try {
            const { invoke } = await import('@tauri-apps/api/core');

            if (isNodeJS) {
                try {
                    const nodeResult = await invoke('check_node_installed') as any;
                    setStatus(prev => ({
                        ...prev,
                        runtime: { loading: false, ...nodeResult }
                    }));
                } catch (_e) {
                    setStatus(prev => ({
                        ...prev,
                        runtime: { loading: false, installed: false, version: null, path: null }
                    }));
                }

                try {
                    const pkgResult = await invoke('check_pkg_installed') as any;
                    setStatus(prev => ({
                        ...prev,
                        compiler: { loading: false, ...pkgResult }
                    }));
                } catch (_e) {
                    setStatus(prev => ({
                        ...prev,
                        compiler: { loading: false, installed: false, version: null }
                    }));
                }
            } else {
                try {
                    const pythonResult = await invoke('check_python_installed') as any;
                    setStatus(prev => ({
                        ...prev,
                        runtime: { loading: false, ...pythonResult }
                    }));

                    const nuitkaResult = await invoke('get_nuitka_status') as any;
                    setStatus(prev => ({
                        ...prev,
                        compiler: { loading: false, ...nuitkaResult }
                    }));
                } catch (_e) {
                    setStatus(prev => ({
                        ...prev,
                        runtime: { loading: false, installed: false, version: null, path: null },
                        compiler: { loading: false, installed: false, version: null }
                    }));
                }
            }

            try {
                const nsisResult = await invoke('check_nsis_installed') as any;
                setStatus(prev => ({
                    ...prev,
                    nsis: { loading: false, ...nsisResult }
                }));
            } catch (_e) {
                setStatus(prev => ({
                    ...prev,
                    nsis: { loading: false, installed: false, version: null }
                }));
            }
        } catch (err: any) {
            setError(err.toString());
            setStatus({
                runtime: { loading: false, installed: false, version: null, path: null },
                compiler: { loading: false, installed: false, version: null },
                nsis: { loading: false, installed: false, version: null }
            });
        }
    }, [isNodeJS]);

    useEffect(() => {
        if (isOpen) {
            checkAll();
        }
    }, [isOpen, checkAll]);

    const installCompiler = useCallback(async () => {
        setInstalling('compiler');
        setError(null);

        try {
            const { invoke } = await import('@tauri-apps/api/core');
            if (isNodeJS) {
                await invoke('install_pkg');
            } else {
                await invoke('install_nuitka');
            }
            await checkAll();
        } catch (err: any) {
            const compilerName = isNodeJS ? 'pkg' : 'Nuitka';
            setError(`Failed to install ${compilerName}: ${err}`);
        } finally {
            setInstalling(null);
        }
    }, [isNodeJS, checkAll]);

    const config = isNodeJS ? {
        title: 'Node.js',
        runtimeName: 'Node.js',
        runtimeDownloadUrl: 'https://nodejs.org/en/download/',
        compilerName: 'pkg (via npx)',
        compilerDesc: 'Auto-downloads when needed',
        runtimeNotFoundMsg: 'Node.js is required. Please install Node.js 18+ and restart the app.',
        noInstallButton: true
    } : {
        title: 'Python',
        runtimeName: 'Python',
        runtimeDownloadUrl: 'https://www.python.org/downloads/',
        compilerName: 'Nuitka Compiler',
        compilerDesc: 'Compiles Python to native code',
        runtimeNotFoundMsg: 'Python is required. Please install Python 3.8+ and restart the app.'
    };

    const allReady = isNodeJS
        ? status.runtime.installed
        : (status.runtime.installed && status.compiler.installed);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4 animate-fade-in">
            <div className="bg-slate-900 rounded-2xl p-6 max-w-md w-full border border-white/10 shadow-2xl">
                <h2 className="text-xl font-bold text-white mb-2">Build Requirements</h2>
                <p className="text-slate-400 text-sm mb-6">
                    These tools are needed to compile your {config.title} project
                </p>

                <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl mb-3">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${status.runtime.loading ? 'bg-slate-500/20' :
                            status.runtime.installed ? 'bg-emerald-500/20' : 'bg-red-500/20'
                            }`}>
                            {status.runtime.loading ? (
                                <Loader2 size={20} className="text-slate-400 animate-spin" />
                            ) : status.runtime.installed ? (
                                <CheckCircle size={20} className="text-emerald-400" />
                            ) : (
                                <XCircle size={20} className="text-red-400" />
                            )}
                        </div>
                        <div>
                            <h3 className="font-medium text-white">{config.runtimeName}</h3>
                            <p className="text-xs text-slate-400">
                                {status.runtime.loading ? 'Checking...' :
                                    status.runtime.installed ? `v${status.runtime.version}` : 'Not found'}
                            </p>
                        </div>
                    </div>
                    {!status.runtime.loading && !status.runtime.installed && (
                        <a
                            href={config.runtimeDownloadUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
                        >
                            Download <ExternalLink size={12} />
                        </a>
                    )}
                </div>

                <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl mb-4">
                    <div className="flex items-center gap-3">
                        {(() => {
                            const compilerReady = isNodeJS
                                ? status.runtime.installed
                                : status.compiler.installed;
                            return (
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${status.compiler.loading ? 'bg-slate-500/20' :
                                    compilerReady ? 'bg-emerald-500/20' : 'bg-amber-500/20'
                                    }`}>
                                    {status.compiler.loading ? (
                                        <Loader2 size={20} className="text-slate-400 animate-spin" />
                                    ) : compilerReady ? (
                                        <CheckCircle size={20} className="text-emerald-400" />
                                    ) : (
                                        <AlertTriangle size={20} className="text-amber-400" />
                                    )}
                                </div>
                            );
                        })()}
                        <div>
                            <h3 className="font-medium text-white">{config.compilerName}</h3>
                            <p className="text-xs text-slate-400">
                                {status.compiler.loading ? 'Checking...' :
                                    (isNodeJS && status.runtime.installed) ? 'Ready (via npx)' :
                                        status.compiler.installed ? status.compiler.version :
                                            config.noInstallButton ? 'Will auto-download' : 'Not installed'}
                            </p>
                        </div>
                    </div>
                    {!config.noInstallButton && !status.compiler.loading && !status.compiler.installed && status.runtime.installed && (
                        <button
                            onClick={installCompiler}
                            disabled={installing === 'compiler'}
                            className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
                        >
                            {installing === 'compiler' ? (
                                <><Loader2 size={14} className="animate-spin" /> Installing...</>
                            ) : (
                                <><Download size={14} /> Install</>
                            )}
                        </button>
                    )}
                </div>

                <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl mb-4">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${status.nsis.loading ? 'bg-slate-500/20' :
                                status.nsis.installed ? 'bg-emerald-500/20' : 'bg-amber-500/20'
                            }`}>
                            {status.nsis.loading ? (
                                <Loader2 size={20} className="text-slate-400 animate-spin" />
                            ) : status.nsis.installed ? (
                                <CheckCircle size={20} className="text-emerald-400" />
                            ) : (
                                <AlertTriangle size={20} className="text-amber-400" />
                            )}
                        </div>
                        <div>
                            <h3 className="font-medium text-white">NSIS Installer</h3>
                            <p className="text-xs text-slate-400">
                                {status.nsis.loading ? 'Checking...' :
                                    status.nsis.installed ? `${status.nsis.version} (Optional)` :
                                        'Not installed (Optional)'}
                            </p>
                        </div>
                    </div>
                    {!status.nsis.loading && !status.nsis.installed && (
                        <a
                            href="https://nsis.sourceforge.io/Download"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
                        >
                            Download <ExternalLink size={12} />
                        </a>
                    )}
                </div>

                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-4">
                        <p className="text-sm text-red-400">{error}</p>
                    </div>
                )}

                {!status.runtime.loading && !status.runtime.installed && (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg mb-4">
                        <p className="text-sm text-amber-400">
                            {config.runtimeNotFoundMsg}
                        </p>
                    </div>
                )}

                <div className="flex gap-3 mt-6">
                    <button
                        onClick={onDismiss}
                        className="flex-1 py-3 rounded-xl font-medium bg-white/10 text-white hover:bg-white/20 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={allReady ? onReady : checkAll}
                        disabled={status.runtime.loading || status.compiler.loading}
                        className={`flex-1 py-3 rounded-xl font-medium transition-all ${allReady
                            ? 'bg-emerald-600 text-white hover:bg-emerald-500'
                            : 'bg-indigo-600 text-white hover:bg-indigo-500'
                            }`}
                    >
                        {allReady ? 'Continue to Build' : 'Recheck'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PrerequisitesCheck;

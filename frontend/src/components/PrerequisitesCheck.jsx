import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Loader2, Download, AlertTriangle, ExternalLink } from 'lucide-react';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

/**
 * PrerequisitesCheck - Modal component to verify build requirements
 * Supports both Python (Nuitka) and Node.js (pkg) builds
 */
const PrerequisitesCheck = ({ isOpen, onReady, onDismiss, language = 'python' }) => {
    const isNodeJS = language === 'nodejs';

    const [status, setStatus] = useState({
        runtime: { loading: true, installed: false, version: null, path: null },
        compiler: { loading: true, installed: false, version: null },
        nsis: { loading: true, installed: false, version: null }  // NSIS for Windows installer
    });
    const [installing, setInstalling] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && isTauri) {
            checkAll();
        }
    }, [isOpen, language]);

    const checkAll = async () => {
        setStatus({
            runtime: { loading: true, installed: false, version: null, path: null },
            compiler: { loading: true, installed: false, version: null },
            nsis: { loading: true, installed: false, version: null }
        });
        setError(null);

        try {
            const { invoke } = await import('@tauri-apps/api/core');

            if (isNodeJS) {
                // Check Node.js
                try {
                    const nodeResult = await invoke('check_node_installed');
                    setStatus(prev => ({
                        ...prev,
                        runtime: { loading: false, ...nodeResult }
                    }));
                } catch (e) {
                    // Fallback: assume Node.js is installed if we can't check
                    setStatus(prev => ({
                        ...prev,
                        runtime: { loading: false, installed: true, version: 'detected', path: null }
                    }));
                }

                // Check pkg
                try {
                    const pkgResult = await invoke('check_pkg_installed');
                    setStatus(prev => ({
                        ...prev,
                        compiler: { loading: false, ...pkgResult }
                    }));
                } catch (e) {
                    // Fallback check
                    setStatus(prev => ({
                        ...prev,
                        compiler: { loading: false, installed: false, version: null }
                    }));
                }
            } else {
                // Check Python
                const pythonResult = await invoke('check_python_installed');
                setStatus(prev => ({
                    ...prev,
                    runtime: { loading: false, ...pythonResult }
                }));

                // Check Nuitka
                const nuitkaResult = await invoke('get_nuitka_status');
                setStatus(prev => ({
                    ...prev,
                    compiler: { loading: false, ...nuitkaResult }
                }));
            }

            // Check NSIS (for installer mode)
            try {
                const nsisResult = await invoke('check_nsis_installed');
                setStatus(prev => ({
                    ...prev,
                    nsis: { loading: false, ...nsisResult }
                }));
            } catch (e) {
                // NSIS check failed - mark as not installed
                setStatus(prev => ({
                    ...prev,
                    nsis: { loading: false, installed: false, version: null }
                }));
            }
        } catch (err) {
            setError(err.toString());
            setStatus({
                runtime: { loading: false, installed: false, version: null, path: null },
                compiler: { loading: false, installed: false, version: null },
                nsis: { loading: false, installed: false, version: null }
            });
        }
    };

    const installCompiler = async () => {
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
        } catch (err) {
            const compilerName = isNodeJS ? 'pkg' : 'Nuitka';
            setError(`Failed to install ${compilerName}: ${err}`);
        } finally {
            setInstalling(null);
        }
    };

    // Config based on language
    const config = isNodeJS ? {
        title: 'Node.js',
        runtimeName: 'Node.js',
        runtimeDownloadUrl: 'https://nodejs.org/en/download/',
        compilerName: 'pkg (via npx)',
        compilerDesc: 'Auto-downloads when needed',
        runtimeNotFoundMsg: 'Node.js is required. Please install Node.js 18+ and restart the app.',
        noInstallButton: true  // pkg via npx doesn't need manual install
    } : {
        title: 'Python',
        runtimeName: 'Python',
        runtimeDownloadUrl: 'https://www.python.org/downloads/',
        compilerName: 'Nuitka Compiler',
        compilerDesc: 'Compiles Python to native code',
        runtimeNotFoundMsg: 'Python is required. Please install Python 3.8+ and restart the app.'
    };

    // For Node.js: npx comes bundled with Node.js, so if Node.js is installed, we're ready
    // For Python: both Python and Nuitka must be installed
    const allReady = isNodeJS
        ? status.runtime.installed  // npx is bundled with Node.js
        : (status.runtime.installed && status.compiler.installed);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4 animate-fade-in">
            <div className="bg-slate-900 rounded-2xl p-6 max-w-md w-full border border-white/10 shadow-2xl">
                <h2 className="text-xl font-bold text-white mb-2">Build Requirements</h2>
                <p className="text-slate-400 text-sm mb-6">
                    These tools are needed to compile your {config.title} project
                </p>

                {/* Runtime Check (Python/Node.js) */}
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

                {/* Compiler Check (Nuitka/pkg) */}
                <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl mb-4">
                    <div className="flex items-center gap-3">
                        {/* For Node.js: show green if runtime is installed (npx bundled with Node.js) */}
                        {(() => {
                            const compilerReady = isNodeJS
                                ? status.runtime.installed  // npx comes with Node.js
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
                    {/* Only show Install button if not using npx (Python only) */}
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

                {/* NSIS Installer Check (Optional - for Windows installer mode) */}
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

                {/* Error Display */}
                {error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-4">
                        <p className="text-sm text-red-400">{error}</p>
                    </div>
                )}

                {/* Runtime Not Found Warning */}
                {!status.runtime.loading && !status.runtime.installed && (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg mb-4">
                        <p className="text-sm text-amber-400">
                            {config.runtimeNotFoundMsg}
                        </p>
                    </div>
                )}

                {/* Action Buttons */}
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

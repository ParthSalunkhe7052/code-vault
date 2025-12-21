import React, { useEffect, useState, useRef } from 'react';
import { X, Terminal, CheckCircle, XCircle, Loader2, FolderOpen } from 'lucide-react';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

const CompilationModal = ({
    isOpen,
    onClose,
    projectPath,
    entryFile,
    outputName,
    outputDir,
    licenseKey,
    showConsole = true,
    onComplete,
    // New build options
    bundleRequirements = false,
    envValues = null,
    buildFrontend = false,
    splitFrontend = false,
    createLauncher = true,
    frontendDir = null
}) => {
    const [status, setStatus] = useState('idle'); // idle, running, completed, failed
    const [progress, setProgress] = useState(0);
    const [logs, setLogs] = useState([]);
    const [outputPath, setOutputPath] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);
    const logsEndRef = useRef(null);

    // Auto-scroll logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    // Listen to Tauri events
    useEffect(() => {
        if (!isTauri || !isOpen) return;

        let unlistenProgress = null;
        let unlistenResult = null;

        const setupListeners = async () => {
            const { listen } = await import('@tauri-apps/api/event');

            unlistenProgress = await listen('compilation-progress', (event) => {
                const { progress: prog, message, stage } = event.payload;
                setProgress(prog);
                // Limit logs to last 500 entries to prevent memory issues
                setLogs(prev => [...prev.slice(-499), {
                    type: stage === 'error' ? 'error' : stage === 'warning' ? 'warning' : 'info',
                    message
                }]);
            });

            unlistenResult = await listen('compilation-result', (event) => {
                const { success, output_path, error_message } = event.payload;
                if (success) {
                    setStatus('completed');
                    setOutputPath(output_path);
                    setProgress(100);
                } else {
                    setStatus('failed');
                    setErrorMessage(error_message);
                }
            });
        };

        setupListeners();

        return () => {
            // Properly cleanup event listeners - these are Promises that resolve to unlisten functions
            unlistenProgress?.then?.(fn => fn?.());
            unlistenResult?.then?.(fn => fn?.());
        };
    }, [isOpen]);

    const startCompilation = async () => {
        if (!isTauri) {
            setLogs([{ type: 'error', message: 'Compilation only available in desktop app' }]);
            setStatus('failed');
            return;
        }

        setStatus('running');
        setProgress(0);
        setLogs([{ type: 'info', message: 'Initializing compilation...' }]);

        try {
            const { invoke } = await import('@tauri-apps/api/core');

            await invoke('run_nuitka_compilation', {
                request: {
                    project_path: projectPath,
                    entry_file: entryFile,
                    output_name: outputName || entryFile.replace(/\.(py|js|ts|mjs|cjs)$/, ''),
                    output_dir: outputDir || null,
                    license_key: licenseKey || null,
                    server_url: 'http://localhost:8000', // License server URL
                    onefile: true,
                    console: showConsole,
                    icon_path: null,
                    // New enhanced options
                    bundle_requirements: bundleRequirements,
                    env_values: envValues,
                    build_frontend: buildFrontend,
                    split_frontend: splitFrontend,
                    create_launcher: createLauncher,
                    frontend_dir: frontendDir,
                }
            });
        } catch (error) {
            setStatus('failed');
            setErrorMessage(error.toString());
            setLogs(prev => [...prev, { type: 'error', message: error.toString() }]);
        }
    };

    const openOutputFolder = async () => {
        if (!outputPath || !isTauri) return;

        try {
            const { invoke } = await import('@tauri-apps/api/core');
            // Handle both forward and backslash for cross-platform
            const lastSep = Math.max(outputPath.lastIndexOf('/'), outputPath.lastIndexOf('\\'));
            const folderPath = lastSep > 0 ? outputPath.substring(0, lastSep) : outputPath;
            await invoke('open_output_folder', { path: folderPath });
        } catch (error) {
            console.error('Failed to open folder:', error);
        }
    };

    const handleClose = () => {
        if (status === 'running') return; // Don't allow closing while running
        onClose();
        // Reset state
        setTimeout(() => {
            setStatus('idle');
            setProgress(0);
            setLogs([]);
            setOutputPath(null);
            setErrorMessage(null);
        }, 300);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={status !== 'running' ? handleClose : undefined}
            />

            {/* Modal */}
            <div className="relative bg-gray-900 border border-white/10 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <Terminal className="text-primary" size={24} />
                        <h2 className="text-lg font-semibold text-white">
                            {status === 'idle' ? 'Compile Project' :
                                status === 'running' ? 'Compiling...' :
                                    status === 'completed' ? 'Compilation Complete!' : 'Compilation Failed'}
                        </h2>
                    </div>
                    {status !== 'running' && (
                        <button
                            onClick={handleClose}
                            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                        >
                            <X size={20} className="text-slate-400" />
                        </button>
                    )}
                </div>

                {/* Content */}
                <div className="p-4 space-y-4">
                    {/* Project Info */}
                    <div className="bg-white/5 rounded-lg p-3 space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Entry File:</span>
                            <span className="text-white font-mono">{entryFile}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Output:</span>
                            <span className="text-white font-mono">{outputName || entryFile.replace(/\.(py|js|ts|mjs|cjs)$/, '.exe')}</span>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    {status !== 'idle' && (
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-slate-400">Progress</span>
                                <span className="text-white font-mono">{progress}%</span>
                            </div>
                            <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                                <div
                                    className={`h-full transition-all duration-300 ${status === 'completed' ? 'bg-emerald-500' :
                                        status === 'failed' ? 'bg-red-500' :
                                            'bg-primary'
                                        }`}
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Logs */}
                    {logs.length > 0 && (
                        <div className="bg-black/50 rounded-lg p-3 h-48 overflow-y-auto font-mono text-xs">
                            {logs.map((log, i) => (
                                <div
                                    key={i}
                                    className={`py-0.5 ${log.type === 'error' ? 'text-red-400' :
                                        log.type === 'warning' ? 'text-amber-400' :
                                            'text-slate-300'
                                        }`}
                                >
                                    {log.message}
                                </div>
                            ))}
                            <div ref={logsEndRef} />
                        </div>
                    )}

                    {/* Status Messages */}
                    {status === 'completed' && outputPath && (
                        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
                            <div className="flex items-center gap-3">
                                <CheckCircle className="text-emerald-400 flex-shrink-0" size={20} />
                                <p className="text-emerald-400 text-sm font-medium">Build successful!</p>
                            </div>
                            <div className="flex items-center justify-between mt-2 gap-3">
                                <p className="text-emerald-300/70 text-xs truncate flex-1 min-w-0" title={outputPath}>
                                    {outputPath.length > 50
                                        ? '...' + outputPath.slice(-47)
                                        : outputPath}
                                </p>
                                <button
                                    onClick={openOutputFolder}
                                    className="flex-shrink-0 flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 rounded-lg text-emerald-400 text-sm transition-colors whitespace-nowrap"
                                >
                                    <FolderOpen size={16} />
                                    Open Folder
                                </button>
                            </div>
                        </div>
                    )}

                    {status === 'failed' && (
                        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                            <XCircle className="text-red-400 flex-shrink-0" size={20} />
                            <div>
                                <p className="text-red-400 text-sm font-medium">Compilation failed</p>
                                <p className="text-red-300/70 text-xs">{errorMessage || 'Unknown error occurred'}</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 p-4 border-t border-white/10 bg-white/5">
                    {status === 'idle' && (
                        <>
                            <button
                                onClick={handleClose}
                                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={startCompilation}
                                className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/80 text-white rounded-lg transition-colors"
                            >
                                <Terminal size={16} />
                                Start Compilation
                            </button>
                        </>
                    )}

                    {status === 'running' && (
                        <div className="flex items-center gap-2 text-slate-400">
                            <Loader2 className="animate-spin" size={16} />
                            <span>Compilation in progress...</span>
                        </div>
                    )}

                    {(status === 'completed' || status === 'failed') && (
                        <button
                            onClick={handleClose}
                            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
                        >
                            Close
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CompilationModal;

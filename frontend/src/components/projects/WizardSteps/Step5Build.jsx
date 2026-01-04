import React, { useState } from 'react';
import { Hammer, FileCode, Terminal, Shield, CheckCircle, Loader, AlertCircle, FolderOpen, Download, Square, XCircle, Copy, Check, ExternalLink, Package } from 'lucide-react';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

/**
 * Step5Build - Final step, shows CLI setup for web mode or build controls for desktop
 */
const Step5Build = ({
    project,
    entryFile,
    showConsole,
    protectionMode = 'generic',
    demoDuration = 60,
    fileTree,
    isBuilding,
    buildProgress,
    buildStatus,
    buildLogs = [],
    outputPath,
    projectPath,
    onBrowseProjectPath,
    onStartBuild,
    onStopBuild,
    onOpenOutputFolder,
    // Distribution settings
    distributionType,
    setDistributionType,
    createDesktopShortcut,
    setCreateDesktopShortcut,
    createStartMenu,
    setCreateStartMenu,
    publisher,
    setPublisher
}) => {
    const [copiedStep, setCopiedStep] = useState(null);

    const copyToClipboard = async (text, stepId) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedStep(stepId);
            setTimeout(() => setCopiedStep(null), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const getStatusColor = () => {
        switch (buildStatus) {
            case 'completed': return 'emerald';
            case 'failed': return 'red';
            case 'cancelled': return 'amber';
            case 'running': return 'indigo';
            default: return 'slate';
        }
    };

    const isNodeJS = project?.language === 'nodejs';
    const projectId = project?.id || '<project-id>';

    // CLI Commands - using local path since not published to PyPI yet
    const installStep1 = 'cd CodeVaultV1\\cli';
    const installStep2 = 'pip install -e .';
    const loginCmd = 'python lw_compiler.py login';
    const buildCmd = `python lw_compiler.py build ${projectId}`;

    // Render CLI Setup Guide for Web Mode (non-Tauri)
    const renderWebModeGuide = () => (
        <div className="space-y-6">
            {/* Header */}
            <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 mb-4">
                    <Terminal size={32} className="text-emerald-400" />
                </div>
                <h2 className="text-xl font-bold text-white mb-2">Build with CLI</h2>
                <p className="text-slate-400 text-sm max-w-md mx-auto">
                    Your project is configured! Follow these steps to build your executable locally.
                </p>
            </div>

            {/* Step 1: Install CLI */}
            <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-xl p-5 border border-purple-500/20">
                <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-lg font-bold text-purple-400">1</span>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-white mb-1">Install the CLI Tool</h3>
                        <p className="text-sm text-slate-400 mb-3">
                            Open your terminal and navigate to the CLI folder, then install:
                        </p>
                        <div className="space-y-2">
                            <div className="relative">
                                <div className="bg-black/40 rounded-lg p-3 font-mono text-sm text-emerald-400 pr-12">
                                    {installStep1}
                                </div>
                                <button
                                    onClick={() => copyToClipboard(installStep1, 'install1')}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-lg transition-colors"
                                    title="Copy command"
                                >
                                    {copiedStep === 'install1' ? (
                                        <Check size={18} className="text-emerald-400" />
                                    ) : (
                                        <Copy size={18} className="text-slate-400" />
                                    )}
                                </button>
                            </div>
                            <div className="relative">
                                <div className="bg-black/40 rounded-lg p-3 font-mono text-sm text-emerald-400 pr-12">
                                    {installStep2}
                                </div>
                                <button
                                    onClick={() => copyToClipboard(installStep2, 'install2')}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-lg transition-colors"
                                    title="Copy command"
                                >
                                    {copiedStep === 'install2' ? (
                                        <Check size={18} className="text-emerald-400" />
                                    ) : (
                                        <Copy size={18} className="text-slate-400" />
                                    )}
                                </button>
                            </div>
                        </div>
                        <p className="text-xs text-slate-500 mt-2">
                            ⚡ This only needs to be done once. Stay in the cli folder for the next steps.
                        </p>
                    </div>
                </div>
            </div>

            {/* Step 2: Login */}
            <div className="bg-gradient-to-br from-blue-500/10 to-indigo-500/10 rounded-xl p-5 border border-blue-500/20">
                <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-lg font-bold text-blue-400">2</span>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-white mb-1">Login to Your Account</h3>
                        <p className="text-sm text-slate-400 mb-3">
                            Use your CodeVault email and password to authenticate:
                        </p>
                        <div className="relative">
                            <div className="bg-black/40 rounded-lg p-4 font-mono text-sm text-emerald-400 pr-12 break-all">
                                {loginCmd}
                            </div>
                            <button
                                onClick={() => copyToClipboard(loginCmd, 'login')}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-lg transition-colors"
                                title="Copy command"
                            >
                                {copiedStep === 'login' ? (
                                    <Check size={18} className="text-emerald-400" />
                                ) : (
                                    <Copy size={18} className="text-slate-400" />
                                )}
                            </button>
                        </div>
                        <p className="text-xs text-slate-500 mt-2">
                            🔐 Your credentials are stored locally and never shared
                        </p>
                    </div>
                </div>
            </div>

            {/* Step 3: Build */}
            <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 rounded-xl p-5 border border-emerald-500/20">
                <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                        <span className="text-lg font-bold text-emerald-400">3</span>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-white mb-1">Build Your Project</h3>
                        <p className="text-sm text-slate-400 mb-3">
                            Run this command to compile your {isNodeJS ? 'JavaScript' : 'Python'} project:
                        </p>
                        <div className="relative">
                            <div className="bg-black/40 rounded-lg p-4 font-mono text-sm text-emerald-400 pr-12 break-all">
                                {buildCmd}
                            </div>
                            <button
                                onClick={() => copyToClipboard(buildCmd, 'build')}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-lg transition-colors"
                                title="Copy command"
                            >
                                {copiedStep === 'build' ? (
                                    <Check size={18} className="text-emerald-400" />
                                ) : (
                                    <Copy size={18} className="text-slate-400" />
                                )}
                            </button>
                        </div>
                        <p className="text-xs text-slate-500 mt-2">
                            ⏱️ First build takes 5-10 minutes to download compilers
                        </p>
                    </div>
                </div>
            </div>

            {/* Build Summary Card */}
            <div className="bg-white/5 rounded-xl border border-white/10 p-5">
                <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                    <FileCode size={18} className="text-indigo-400" />
                    Your Build Configuration
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="bg-black/20 rounded-lg p-3">
                        <span className="text-slate-400 block mb-1">Entry File</span>
                        <span className="text-white font-mono">{entryFile || 'Not set'}</span>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3">
                        <span className="text-slate-400 block mb-1">Language</span>
                        <span className="text-white">{isNodeJS ? 'Node.js' : 'Python'}</span>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3">
                        <span className="text-slate-400 block mb-1">Protection</span>
                        <span className="text-white capitalize">{protectionMode === 'demo' ? `Demo (${demoDuration}min)` : protectionMode}</span>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3">
                        <span className="text-slate-400 block mb-1">Files</span>
                        <span className="text-white">{fileTree?.total_files || 0} files</span>
                    </div>
                </div>
            </div>

            {/* Requirements Note */}
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                <h4 className="font-semibold text-amber-400 mb-2 flex items-center gap-2">
                    <AlertCircle size={18} />
                    Requirements
                </h4>
                <ul className="text-sm text-slate-300 space-y-1.5">
                    {isNodeJS ? (
                        <>
                            <li className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                Node.js 16+ installed
                            </li>
                            <li className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                pkg will be installed automatically
                            </li>
                        </>
                    ) : (
                        <>
                            <li className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                Python 3.8+ installed
                            </li>
                            <li className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                                Nuitka will be installed automatically (first build)
                            </li>
                        </>
                    )}
                    <li className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                        Windows PC (cross-compilation not supported)
                    </li>
                </ul>
            </div>

            {/* Help Link */}
            <div className="text-center text-sm text-slate-400">
                Need help?{' '}
                <a
                    href="/docs/cli-guide"
                    className="text-indigo-400 hover:text-indigo-300 hover:underline inline-flex items-center gap-1"
                >
                    Read the CLI Guide
                    <ExternalLink size={14} />
                </a>
            </div>
        </div>
    );

    // Render Desktop Build Controls (Tauri)
    const renderDesktopBuild = () => (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white mb-2">Build Your Executable</h2>
                <p className="text-slate-400 text-sm">
                    Review your settings and start the build process
                </p>
            </div>

            {/* Project Path Selector (Required for Tauri builds) */}
            <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 rounded-xl border border-amber-500/20 p-5">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                        <FolderOpen size={20} className="text-amber-400" />
                        <div>
                            <h3 className="font-semibold text-white">Project Folder</h3>
                            <p className="text-xs text-slate-400">Where your {isNodeJS ? 'JavaScript' : 'Python'} files are located</p>
                        </div>
                    </div>
                    <button
                        onClick={onBrowseProjectPath}
                        className="px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 rounded-lg text-sm transition-colors"
                    >
                        Browse...
                    </button>
                </div>

                {projectPath ? (
                    <div className="bg-black/30 rounded-lg p-3 font-mono text-sm text-emerald-400 break-all">
                        {projectPath}
                    </div>
                ) : (
                    <div className="bg-black/30 rounded-lg p-3 text-sm text-slate-500 italic">
                        No folder selected - click Browse to select your project folder
                    </div>
                )}
            </div>

            {/* Distribution Type Selector */}
            <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-xl border border-indigo-500/20 p-5">
                <div className="flex items-center gap-3 mb-4">
                    <Download size={20} className="text-indigo-400" />
                    <div>
                        <h3 className="font-semibold text-white">Distribution Method</h3>
                        <p className="text-xs text-slate-400">Choose how to package your application</p>
                    </div>
                </div>

                {/* Radio buttons for Portable vs Installer */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                    <button
                        onClick={() => setDistributionType('portable')}
                        className={`p-4 rounded-lg border-2 transition-all text-left ${distributionType === 'portable'
                            ? 'border-indigo-500 bg-indigo-500/20'
                            : 'border-white/10 bg-white/5 hover:border-white/20'
                            }`}
                    >
                        <div className="font-medium text-white mb-1">Portable .exe</div>
                        <div className="text-xs text-slate-400">Single executable file</div>
                    </button>

                    <button
                        onClick={() => setDistributionType('installer')}
                        className={`p-4 rounded-lg border-2 transition-all text-left ${distributionType === 'installer'
                            ? 'border-indigo-500 bg-indigo-500/20'
                            : 'border-white/10 bg-white/5 hover:border-white/20'
                            }`}
                    >
                        <div className="font-medium text-white mb-1">Windows Installer</div>
                        <div className="text-xs text-slate-400">Professional NSIS installer</div>
                    </button>
                </div>

                {/* Installer Options */}
                {distributionType === 'installer' && (
                    <div className="space-y-3 bg-black/20 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                            <label className="text-sm text-white">Create Desktop Shortcut</label>
                            <button
                                onClick={() => setCreateDesktopShortcut(!createDesktopShortcut)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${createDesktopShortcut ? 'bg-indigo-500' : 'bg-white/20'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${createDesktopShortcut ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>

                        <div className="flex items-center justify-between">
                            <label className="text-sm text-white">Create Start Menu Entry</label>
                            <button
                                onClick={() => setCreateStartMenu(!createStartMenu)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${createStartMenu ? 'bg-indigo-500' : 'bg-white/20'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${createStartMenu ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>

                        <div>
                            <label className="text-sm text-white block mb-2">Publisher Name</label>
                            <input
                                type="text"
                                value={publisher}
                                onChange={(e) => setPublisher(e.target.value)}
                                placeholder="Your Company Name"
                                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Build Summary */}
            <div className="bg-white/5 rounded-xl border border-white/10 divide-y divide-white/10">
                <div className="p-4 flex items-center gap-4">
                    <FileCode size={20} className="text-emerald-400" />
                    <div className="flex-1">
                        <p className="text-xs text-slate-400">Entry Point</p>
                        <p className="text-white font-mono">{entryFile || 'Not selected'}</p>
                    </div>
                </div>

                <div className="p-4 flex items-center gap-4">
                    <Terminal size={20} className="text-blue-400" />
                    <div className="flex-1">
                        <p className="text-xs text-slate-400">Console Mode</p>
                        <p className="text-white">{showConsole ? 'Show console window' : 'No console (GUI app)'}</p>
                    </div>
                </div>

                <div className="p-4 flex items-center gap-4">
                    <Shield size={20} className="text-purple-400" />
                    <div className="flex-1">
                        <p className="text-xs text-slate-400">Protection Mode</p>
                        <p className="text-white text-sm">
                            {protectionMode === 'demo'
                                ? `Trial Mode (${demoDuration >= 1440 ? Math.floor(demoDuration / 1440) + ' days' : demoDuration >= 60 ? Math.floor(demoDuration / 60) + ' hours' : demoDuration + ' min'})`
                                : protectionMode === 'none'
                                    ? 'No Protection'
                                    : 'Generic Build (runtime key)'}
                        </p>
                    </div>
                </div>

                {fileTree && (
                    <div className="p-4 flex items-center gap-4">
                        <FolderOpen size={20} className="text-amber-400" />
                        <div className="flex-1">
                            <p className="text-xs text-slate-400">Project Files</p>
                            <p className="text-white">{fileTree.total_files} files</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Build Progress */}
            {buildStatus && buildStatus !== 'idle' && (
                <div className={`rounded-xl border p-5 ${buildStatus === 'completed' ? 'bg-emerald-500/10 border-emerald-500/30' :
                    buildStatus === 'failed' ? 'bg-red-500/10 border-red-500/30' :
                        'bg-indigo-500/10 border-indigo-500/30'
                    }`}>
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            {buildStatus === 'completed' ? (
                                <CheckCircle size={20} className="text-emerald-400" />
                            ) : buildStatus === 'failed' ? (
                                <AlertCircle size={20} className="text-red-400" />
                            ) : buildStatus === 'cancelled' ? (
                                <XCircle size={20} className="text-amber-400" />
                            ) : (
                                <Loader size={20} className="text-indigo-400 animate-spin" />
                            )}
                            <span className={`font-medium capitalize text-${getStatusColor()}-400`}>
                                {buildStatus}
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            {buildStatus === 'running' && onStopBuild && (
                                <button
                                    onClick={onStopBuild}
                                    className="flex items-center gap-1.5 px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm transition-colors"
                                    title="Stop the build process"
                                >
                                    <Square size={12} fill="currentColor" />
                                    Stop
                                </button>
                            )}
                            <span className="text-sm text-slate-400">{buildProgress}%</span>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden mb-4">
                        <div
                            className={`h-full rounded-full transition-all duration-500 ${buildStatus === 'completed' ? 'bg-emerald-500' :
                                buildStatus === 'failed' ? 'bg-red-500' : 'bg-indigo-500'
                                }`}
                            style={{ width: `${buildProgress}%` }}
                        />
                    </div>

                    {/* Build Logs */}
                    {buildLogs.length > 0 && (
                        <div className="bg-black/30 rounded-lg p-3 font-mono text-xs max-h-40 overflow-y-auto">
                            {buildLogs.slice(-12).map((log, i) => (
                                <div key={i} className="text-slate-300 py-0.5">{log}</div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Output Path & Open Folder (when complete) */}
            {buildStatus === 'completed' && outputPath && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 min-w-0">
                            <CheckCircle size={24} className="text-emerald-400 flex-shrink-0" />
                            <div className="min-w-0">
                                <p className="font-medium text-white truncate">{outputPath.split(/[/\\]/).pop()}</p>
                                <p className="text-xs text-slate-400 truncate" title={outputPath}>{outputPath}</p>
                            </div>
                        </div>
                        <button
                            onClick={onOpenOutputFolder}
                            className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-lg transition-colors flex-shrink-0"
                        >
                            <FolderOpen size={18} />
                            Open Folder
                        </button>
                    </div>
                </div>
            )}

            {/* Start Build Button */}
            {(!buildStatus || buildStatus === 'idle' || buildStatus === 'failed') && (
                <button
                    onClick={onStartBuild}
                    disabled={!entryFile || isBuilding || !projectPath}
                    className={`
                        w-full flex items-center justify-center gap-3 
                        px-6 py-4 rounded-xl font-semibold text-lg 
                        transition-all shadow-lg
                        ${entryFile && !isBuilding && projectPath
                            ? 'bg-gradient-to-r from-emerald-600 to-cyan-600 text-white hover:from-emerald-500 hover:to-cyan-500 shadow-emerald-500/25'
                            : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                        }
                    `}
                >
                    {isBuilding ? (
                        <>
                            <Loader size={22} className="animate-spin" />
                            Building...
                        </>
                    ) : (
                        <>
                            <Hammer size={22} />
                            Start Build
                        </>
                    )}
                </button>
            )}

            {/* Validation Messages */}
            {!entryFile && (
                <p className="text-center text-amber-400 text-sm">
                    ⚠️ Please select an entry file in the Configure step
                </p>
            )}

            {entryFile && !projectPath && (
                <p className="text-center text-amber-400 text-sm">
                    ⚠️ Please select your project folder above
                </p>
            )}
        </div>
    );

    return isTauri ? renderDesktopBuild() : renderWebModeGuide();
};

export default Step5Build;

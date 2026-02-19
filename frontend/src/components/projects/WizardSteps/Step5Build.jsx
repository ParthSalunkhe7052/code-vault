import { useState, memo } from 'react';
import { Hammer, FileCode, Terminal, Shield, CheckCircle, Loader2, AlertCircle, FolderOpen, Download, Square, XCircle, Copy, Check, ExternalLink, Package, Key, Play } from 'lucide-react';
import { CloudBuildButton } from '../../CloudBuildButton';
import PlatformSelector from '../PlatformSelector';
import BuildHistory from '../BuildHistory';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

/**
 * Step5Build - Final step, shows CLI setup for web mode or build controls for desktop
 * REDESIGN: Split view for Mission Control layout
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
    onViewLicenses,
    // Distribution settings
    distributionType,
    setDistributionType,
    createDesktopShortcut,
    setCreateDesktopShortcut,
    createStartMenu,
    setCreateStartMenu,
    publisher,
    setPublisher,
    licenseId,
    // Cross-platform compilation
    isPro = false
}) => {
    const [copiedStep, setCopiedStep] = useState(null);
    const [selectedPlatforms, setSelectedPlatforms] = useState(['windows']);

    const copyToClipboard = async (text, stepId) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedStep(stepId);
            setTimeout(() => setCopiedStep(null), 2000);
        } catch (err) {
            if (import.meta.env.DEV) {
                console.error('Failed to copy:', err);
            }
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

    // Pre-computed Tailwind class maps (dynamic template literals don't work with JIT)
    const statusColorClasses = {
        emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        red: 'bg-red-500/10 text-red-400 border-red-500/20',
        amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
        slate: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    };

    const isNodeJS = project?.language === 'nodejs';
    const projectId = project?.id || '<project-id>';

    // CLI Commands
    const installStep1 = 'pip install codevault-cli';
    const loginCmd = 'codevault auth login';
    const buildCmd = `codevault project build ${projectId}`;
    const buildCmdFast = `codevault project build ${projectId} --fast`;

    // Render CLI Setup Guide for Web Mode (non-Tauri)
    const renderWebModeGuide = () => (
        <div className="space-y-6">
            {/* Cloud Build Section */}
             <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-xl p-6 border border-indigo-500/20">
                <div className="text-center mb-6">
                    <h2 className="text-xl font-bold text-white mb-2">Cloud Build (Recommended)</h2>
                    <p className="text-slate-400 text-sm max-w-md mx-auto mb-4">
                        Compile your project instantly on our secure cloud servers. No local installation required.
                    </p>
                </div>

                {/* Platform Selection */}
                {!isBuilding && (
                    <div className="mb-6">
                        <PlatformSelector
                            selectedPlatforms={selectedPlatforms}
                            onChange={setSelectedPlatforms}
                            isPro={isPro}
                            disabled={false}
                        />
                    </div>
                )}

                {/* Build Button */}
                <div className="max-w-md mx-auto">
                    <CloudBuildButton 
                        projectId={projectId} 
                        licenseId={licenseId} 
                        targetPlatforms={selectedPlatforms}
                        licenseMode={protectionMode}
                        demoDuration={demoDuration}
                        className="w-full"
                    />
                </div>

                {/* Build History */}
                <div className="max-w-md mx-auto mt-6">
                    <BuildHistory 
                        projectId={projectId}
                        onRebuild={(build) => {
                            // Update selected platforms from build history
                            if (build.target_platforms) {
                                setSelectedPlatforms(build.target_platforms);
                            }
                            // Trigger the cloud build button (user will need to click it)
                            // For future enhancement: could auto-trigger build here
                        }}
                    />
                </div>
            </div>

            <div className="relative flex items-center py-4">
                <div className="flex-grow border-t border-white/10"></div>
                <span className="flex-shrink-0 mx-4 text-slate-500 text-sm">OR BUILD LOCALLY</span>
                <div className="flex-grow border-t border-white/10"></div>
            </div>

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
                            Open your terminal and install the CodeVault CLI:
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
                        </div>
                        <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                            <span>Windows only • Python builds free</span>
                        </div>
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
                            Use your CodeVault credentials to authenticate:
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
                            🔐 Your credentials are stored securely on your machine
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
                            Run one of these commands to compile your {isNodeJS ? 'JavaScript' : 'Python'} project:
                        </p>
                        
                        {/* Standard Build */}
                        <div className="relative mb-2">
                            <div className="bg-black/40 rounded-lg p-3 font-mono text-sm text-emerald-400 pr-12 break-all">
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
                        
                        {/* Fast Build */}
                        <div className="relative mb-3">
                            <div className="bg-black/40 rounded-lg p-3 font-mono text-sm text-indigo-400 pr-12 break-all">
                                {buildCmdFast}
                            </div>
                            <button
                                onClick={() => copyToClipboard(buildCmdFast, 'build-fast')}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-white/10 rounded-lg transition-colors"
                                title="Copy command"
                            >
                                {copiedStep === 'build-fast' ? (
                                    <Check size={18} className="text-emerald-400" />
                                ) : (
                                    <Copy size={18} className="text-slate-400" />
                                )}
                            </button>
                        </div>
                        
                        <div className="flex flex-wrap gap-2 text-xs mb-3">
                            <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded">Python: Free</span>
                            {isNodeJS ? (
                                <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded">Node.js: Pro+ Required</span>
                            ) : (
                                <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded">Node.js needs upgrade</span>
                            )}
                            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded">Windows only</span>
                        </div>
                        
                        <p className="text-xs text-slate-500">
                            ⏱️ First build takes 5-10 minutes to download compilers. Use --fast for 3-4x faster builds.
                        </p>
                        
                        {/* View License Key Button */}
                        {onViewLicenses && (
                            <button
                                onClick={onViewLicenses}
                                className="mt-4 w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-indigo-600/20 to-purple-600/20 hover:from-indigo-600/30 hover:to-purple-600/30 border border-indigo-500/30 hover:border-indigo-500/50 text-indigo-300 hover:text-indigo-200 rounded-lg transition-all font-medium"
                            >
                                <Key size={18} />
                                View License Keys
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );

    // Render Desktop Build Controls (Tauri)
    const renderDesktopBuild = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
            
            {/* Left Column: Build Configuration */}
            <div className="space-y-6 flex flex-col">
                <div className="text-left">
                     <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">Build & Output</h2>
                     <p className="text-slate-400">
                        Compile your project into a standalone executable.
                     </p>
                </div>

                {/* Project Path Selector (Required for Tauri builds) */}
                <div className="bg-white/5 rounded-2xl border border-white/10 p-6 hover:border-white/20 transition-all">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center text-amber-400">
                                <FolderOpen size={20} />
                            </div>
                            <div>
                                <h3 className="font-bold text-white">Project Source</h3>
                                <p className="text-xs text-slate-400">Root folder containing {isNodeJS ? 'package.json' : 'requirements.txt'}</p>
                            </div>
                        </div>
                        <button
                            onClick={onBrowseProjectPath}
                            className="px-4 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 rounded-lg text-sm transition-colors border border-amber-500/20"
                        >
                            Browse...
                        </button>
                    </div>

                    {projectPath ? (
                        <div className="bg-black/30 rounded-xl p-3 font-mono text-sm text-emerald-400 break-all border border-white/5 flex items-center gap-2">
                             <CheckCircle size={14} />
                            {projectPath}
                        </div>
                    ) : (
                        <div className="bg-amber-500/5 border border-amber-500/10 rounded-xl p-3 text-sm text-amber-500 flex items-center gap-2">
                            <AlertCircle size={14} />
                            Please select your project folder
                        </div>
                    )}
                </div>

                {/* Distribution Type Selector */}
                <div className="bg-white/5 rounded-2xl border border-white/10 p-6 hover:border-white/20 transition-all">
                    <div className="flex items-center gap-3 mb-4">
                         <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                            <Download size={20} />
                        </div>
                        <div>
                            <h3 className="font-bold text-white">Distribution</h3>
                            <p className="text-xs text-slate-400">Output format</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 mb-4">
                        <button
                            onClick={() => setDistributionType('portable')}
                            className={`p-4 rounded-xl border-2 transition-all text-left ${distributionType === 'portable'
                                ? 'border-indigo-500 bg-indigo-500/20'
                                : 'border-white/5 bg-black/20 hover:border-white/10'
                                }`}
                        >
                            <div className="font-bold text-white mb-1">Portable .exe</div>
                            <div className="text-xs text-slate-400">Single executable file</div>
                        </button>

                        <button
                            onClick={() => setDistributionType('installer')}
                            className={`p-4 rounded-xl border-2 transition-all text-left ${distributionType === 'installer'
                                ? 'border-indigo-500 bg-indigo-500/20'
                                : 'border-white/5 bg-black/20 hover:border-white/10'
                                }`}
                        >
                            <div className="font-bold text-white mb-1">Installer</div>
                            <div className="text-xs text-slate-400">Setup Wizard (NSIS)</div>
                        </button>
                    </div>

                    {/* Installer Options */}
                    {distributionType === 'installer' && (
                        <div className="space-y-3 bg-black/20 rounded-xl p-4 border border-white/5 animate-in slide-in-from-top-2 duration-300">
                            <div className="flex items-center justify-between">
                                <label className="text-sm text-slate-300">Create Desktop Shortcut</label>
                                <button
                                    onClick={() => setCreateDesktopShortcut(!createDesktopShortcut)}
                                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${createDesktopShortcut ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                >
                                    <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${createDesktopShortcut ? 'translate-x-5' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            <div className="flex items-center justify-between">
                                <label className="text-sm text-slate-300">Create Start Menu Entry</label>
                                <button
                                    onClick={() => setCreateStartMenu(!createStartMenu)}
                                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${createStartMenu ? 'bg-indigo-500' : 'bg-slate-700'}`}
                                >
                                    <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${createStartMenu ? 'translate-x-5' : 'translate-x-1'}`} />
                                </button>
                            </div>

                            <div>
                                <label className="text-xs font-semibold text-slate-500 uppercase mb-1 block">Publisher Name</label>
                                <input
                                    type="text"
                                    value={publisher}
                                    onChange={(e) => setPublisher(e.target.value)}
                                    placeholder="Your Company Name"
                                    className="w-full px-3 py-2 bg-black/20 border border-white/10 rounded-lg text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none text-sm"
                                />
                            </div>
                        </div>
                    )}
                </div>

                {/* Validation & Start Button */}
                <div className="mt-auto pt-6">
                     {(!buildStatus || buildStatus === 'idle' || buildStatus === 'failed') && (
                        <button
                            onClick={onStartBuild}
                            disabled={!entryFile || isBuilding || !projectPath}
                            className={`
                                w-full flex items-center justify-center gap-3 
                                px-6 py-4 rounded-xl font-bold text-lg 
                                transition-all shadow-xl group
                                ${entryFile && !isBuilding && projectPath
                                    ? 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-white hover:from-emerald-400 hover:to-cyan-400 shadow-emerald-500/20 hover:shadow-emerald-500/40 hover:-translate-y-1'
                                    : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-white/5'
                                }
                            `}
                        >
                            {isBuilding ? (
                                <>
                                    <Loader2 size={24} className="animate-spin" />
                                    Compiling...
                                </>
                            ) : (
                                <>
                                    <div className="p-2 bg-white/20 rounded-lg group-hover:rotate-12 transition-transform">
                                        <Hammer size={20} className="text-white" />
                                    </div>
                                    Start Compilation
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>

            {/* Right Column: Status & Logs */}
            <div className="bg-black/40 border border-white/10 rounded-2xl overflow-hidden flex flex-col h-[600px] lg:h-auto">
                <div className="p-4 border-b border-white/10 bg-white/5 flex items-center justify-between">
                    <h3 className="font-bold text-white flex items-center gap-2">
                        <Terminal size={18} className="text-slate-400" />
                        Build Output
                    </h3>
                    <div className="flex items-center gap-3">
                         {buildStatus && buildStatus !== 'idle' && (
                            <span className={`flex items-center gap-2 text-xs font-bold px-2 py-1 rounded ${statusColorClasses[getStatusColor()]} uppercase`}>
                                {buildStatus === 'running' && <Loader2 size={12} className="animate-spin" />}
                                {buildStatus}
                            </span>
                         )}
                    </div>
                </div>

                {/* Build in Progress Notification */}
                {buildStatus === 'running' && (
                    <div className="mx-4 mt-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-4 animate-in fade-in slide-in-from-top-2">
                        <div className="flex items-start gap-3">
                            <div className="p-2 bg-indigo-500/20 rounded-lg shrink-0">
                                <Loader2 size={20} className="text-indigo-400 animate-spin" />
                            </div>
                            <div>
                                <h4 className="font-bold text-white mb-1">Build in Progress</h4>
                                <p className="text-sm text-slate-300 mb-3 leading-relaxed">
                                    You can safely <span className="text-white font-semibold">close this wizard</span>. The build will continue in the background.
                                </p>
                                <div className="flex items-center gap-2 text-xs text-indigo-300 bg-indigo-500/10 p-2.5 rounded-lg border border-indigo-500/10">
                                     <Key size={14} className="shrink-0" />
                                     <span>Tip: Switch to the <strong>Licenses</strong> tab to create keys while you wait.</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Logs Area */}
                <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1 custom-scrollbar bg-black/50">
                    {buildLogs.length > 0 ? (
                        buildLogs.map((log, i) => (
                            <div key={i} className="text-slate-300 break-all hover:bg-white/5 p-0.5 rounded px-2 border-l-2 border-transparent hover:border-indigo-500/50">
                                <span className="text-slate-600 select-none mr-2">
                                    {new Date().toLocaleTimeString().split(' ')[0]}
                                </span>
                                {log}
                            </div>
                        ))
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-slate-600">
                            <Terminal size={48} className="mb-4 opacity-20" />
                            <p>Ready to build.</p>
                            <p className="text-[10px] mt-2">Logs will appear here...</p>
                        </div>
                    )}
                </div>

                {/* Build Progress Footer */}
                {buildStatus && buildStatus !== 'idle' && (
                    <div className="p-4 border-t border-white/10 bg-white/5">
                        <div className="flex items-center justify-between mb-2 text-xs">
                             <span className="text-slate-400">Progress</span>
                             <span className="text-white font-mono">{buildProgress}%</span>
                        </div>
                         <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-300 ${
                                    buildStatus === 'completed' ? 'bg-emerald-500' :
                                    buildStatus === 'failed' ? 'bg-red-500' : 'bg-indigo-500'
                                }`}
                                style={{ width: `${buildProgress}%` }}
                            />
                        </div>
                        
                        {buildStatus === 'running' && onStopBuild && (
                             <button
                                onClick={onStopBuild}
                                className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg text-xs transition-colors border border-red-500/20"
                            >
                                <Square size={12} fill="currentColor" />
                                Stop Compilation
                            </button>
                        )}
                    </div>
                )}
                
                {/* Success State */}
                {buildStatus === 'completed' && outputPath && (
                     <div className="p-4 border-t border-white/10 bg-emerald-500/10">
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                                <Check size={20} />
                            </div>
                            <div>
                                <h4 className="font-bold text-white">Build Successful!</h4>
                                <p className="text-xs text-emerald-300/70">Executable created successfully.</p>
                            </div>
                        </div>
                         <button
                            onClick={onOpenOutputFolder}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors font-medium text-sm shadow-lg shadow-emerald-500/20"
                        >
                            <FolderOpen size={18} />
                            Open Output Folder
                        </button>
                     </div>
                )}
            </div>
        </div>
    );

    return isTauri ? renderDesktopBuild() : renderWebModeGuide();
};

const MemoizedStep5Build = memo(Step5Build);

export default MemoizedStep5Build;

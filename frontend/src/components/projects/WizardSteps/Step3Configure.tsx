import React, { useMemo, useCallback, memo } from 'react';
import { FileCode, Terminal, Cpu, Image, Sparkles, Shield, Fingerprint, Box, FolderOpen, AlertCircle, Layers, Lock } from 'lucide-react';
import { usePricing } from '../../../contexts/PricingContext';
import { Project, ProjectFile } from '../../../types/api';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__ !== undefined;

interface Step3ConfigureProps {
    fileTree: any;
    files?: ProjectFile[];
    entryFile: string;
    setEntryFile: (file: string) => void;
    entryPointCandidates?: any[];
    showConsole: boolean;
    setShowConsole: React.Dispatch<React.SetStateAction<boolean>>;
    projectPath?: string;
    envValues?: Record<string, string>;
    selectedEnvKeys?: string[];
    setSelectedEnvKeys: (keys: string[]) => void;
    iconPath: string | null;
    setIconPath: (path: string | null) => void;
    includePackages?: string[];
    setIncludePackages: (packages: string[]) => void;
    excludePackages?: string[];
    setExcludePackages: (packages: string[]) => void;
    detectedDataFolders?: string[];
    selectedDataFolders?: string[];
    setSelectedDataFolders: (folders: string[]) => void;
    project: Project | null;
    nodeTarget: string;
    setNodeTarget: (target: string) => void;
    enableObfuscation?: boolean;
    setEnableObfuscation: (enabled: boolean) => void;
    enableLease?: boolean;
    setEnableLease: (enabled: boolean) => void;
    fastBuild?: boolean;
    setFastBuild: (enabled: boolean) => void;
    enableBinaryHash?: boolean;
    setEnableBinaryHash: (enabled: boolean) => void;
}

const Step3Configure: React.FC<Step3ConfigureProps> = memo(({
    fileTree,
    files = [],
    entryFile,
    setEntryFile,
    entryPointCandidates = [],
    showConsole,
    setShowConsole,
    envValues = {},
    selectedEnvKeys = [],
    setSelectedEnvKeys,
    iconPath,
    setIconPath,
    includePackages = [],
    setIncludePackages,
    excludePackages = [],
    setExcludePackages,
    detectedDataFolders = [],
    selectedDataFolders = [],
    setSelectedDataFolders,
    project,
    nodeTarget,
    setNodeTarget,
    enableObfuscation = false,
    setEnableObfuscation,
    enableLease = true,
    setEnableLease,
    fastBuild = false,
    setFastBuild,
    enableBinaryHash = false,
    setEnableBinaryHash
}) => {
    const isNodeJS = useMemo(() => project?.language === 'nodejs', [project?.language]);

    const sourceFiles = useMemo(() => {
        return fileTree
            ? fileTree.files.filter((f: string) => isNodeJS ? /\.(js|ts|mjs|cjs)$/.test(f) : f.endsWith('.py'))
            : files.filter(f => isNodeJS ? /\.(js|ts|mjs|cjs)$/.test(f.filename) : f.filename.endsWith('.py')).map(f => f.filename);
    }, [fileTree, files, isNodeJS]);

    const getCandidate = useCallback((file: string) => {
        return entryPointCandidates.find(c => c.file === file);
    }, [entryPointCandidates]);

    const browseIcon = useCallback(async () => {
        if (!isTauri) return;

        try {
            const { open } = await import('@tauri-apps/plugin-dialog');
            const selected = await open({
                multiple: false,
                filters: [{
                    name: 'Icon',
                    extensions: ['ico', 'png']
                }],
                title: 'Select Icon File (.ico or .png)'
            });

            if (selected && typeof selected === 'string') {
                if (selected.toLowerCase().endsWith('.png')) {
                    try {
                        const { invoke } = await import('@tauri-apps/api/core');
                        const icoPath = await invoke('convert_png_to_ico', { pngPath: selected }) as string;
                        setIconPath(icoPath);
                    } catch (err) {
                        setIconPath(selected);
                    }
                } else {
                    setIconPath(selected);
                }
            }
        } catch (error) {
            console.error('Failed to open file picker:', error);
        }
    }, [setIconPath]);

    const handleEnvVarChange = useCallback((key: string, checked: boolean) => {
        if (checked) {
            setSelectedEnvKeys([...selectedEnvKeys, key]);
        } else {
            setSelectedEnvKeys(selectedEnvKeys.filter(k => k !== key));
        }
    }, [selectedEnvKeys, setSelectedEnvKeys]);

    const handleDataFolderChange = useCallback((folder: string, checked: boolean) => {
        if (checked) {
            setSelectedDataFolders([...selectedDataFolders, folder]);
        } else {
            setSelectedDataFolders(selectedDataFolders.filter(f => f !== folder));
        }
    }, [selectedDataFolders, setSelectedDataFolders]);

    const handleIncludeChange = useCallback((value: string) => {
        setIncludePackages(value.split(',').map(s => s.trim()).filter(Boolean));
    }, [setIncludePackages]);

    const handleExcludeChange = useCallback((value: string) => {
        setExcludePackages(value.split(',').map(s => s.trim()).filter(Boolean));
    }, [setExcludePackages]);

    const toggleConsole = useCallback(() => {
        setShowConsole(!showConsole);
    }, [showConsole, setShowConsole]);

    const toggleObfuscation = useCallback(() => {
        setEnableObfuscation(!enableObfuscation);
    }, [enableObfuscation, setEnableObfuscation]);

    const toggleLease = useCallback(() => {
        setEnableLease(!enableLease);
    }, [enableLease, setEnableLease]);

    const toggleFastBuild = useCallback(() => {
        setFastBuild(!fastBuild);
    }, [fastBuild, setFastBuild]);

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="text-left">
                <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">Configuration</h2>
                <p className="text-slate-400">
                    Fine-tune your build settings. {isNodeJS ? 'Node.js' : 'Python'} project detected.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 bg-gradient-to-br from-indigo-500/10 to-blue-600/10 rounded-2xl border border-indigo-500/20 p-6 relative overflow-hidden group">
                     <div className="absolute inset-0 bg-indigo-500/5 group-hover:bg-indigo-500/10 transition-colors" />
                     
                     <div className="relative z-10">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400">
                                <FileCode size={20} />
                            </div>
                            <div>
                                <h3 className="font-bold text-white text-lg">Entry Point</h3>
                                <p className="text-xs text-slate-400">Main execution file</p>
                            </div>
                        </div>

                        <select
                            value={entryFile}
                            onChange={(e) => setEntryFile(e.target.value)}
                            className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/50 transition-all text-sm font-mono mb-3 hover:bg-black/40"
                        >
                            <option value="">Select entry file...</option>
                            {sourceFiles.map((file: string, idx: number) => {
                                const candidate = getCandidate(file);
                                return (
                                    <option key={idx} value={file}>
                                        {file} {candidate?.score > 0 ? `(Recommended)` : ''}
                                    </option>
                                );
                            })}
                        </select>

                        {entryPointCandidates.length > 0 && !entryFile && (
                            <div className="flex flex-wrap gap-2">
                                <span className="text-xs text-slate-500 py-1">Suggested:</span>
                                {entryPointCandidates.slice(0, 3).map((candidate, i) => (
                                    <button
                                        key={i}
                                        onClick={() => setEntryFile(candidate.file)}
                                        className="text-xs px-2 py-1 bg-indigo-500/20 text-indigo-300 rounded hover:bg-indigo-500/30 transition-colors font-mono"
                                    >
                                        {candidate.file}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="bg-white/5 rounded-2xl border border-white/10 p-6 flex flex-col justify-between hover:border-white/20 transition-all group">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-slate-700/30 flex items-center justify-center text-slate-300">
                            <Terminal size={20} />
                        </div>
                        <h3 className="font-bold text-white">Console</h3>
                    </div>
                    
                    <p className="text-xs text-slate-400 mb-4 line-clamp-2">
                        Show terminal window on launch. Useful for debugging or CLI apps.
                    </p>

                    <label className="flex items-center gap-3 cursor-pointer select-none self-start">
                        <div className={`w-14 h-8 rounded-full p-1 transition-colors duration-300 ${showConsole ? 'bg-indigo-600' : 'bg-slate-700'}`}>
                            <div className={`w-6 h-6 rounded-full bg-white shadow-sm transition-transform duration-300 ${showConsole ? 'translate-x-6' : 'translate-x-0'}`} />
                        </div>
                        <span className={`text-sm font-medium ${showConsole ? 'text-indigo-400' : 'text-slate-500'}`}>
                            {showConsole ? 'Visible' : 'Hidden'}
                        </span>
                        <input type="checkbox" checked={showConsole} onChange={toggleConsole} className="hidden" />
                    </label>
                </div>
            </div>

            <div className="border-t border-white/10 my-6" />

            {isNodeJS ? (
                <ObfuscationToggleCard 
                    enableObfuscation={enableObfuscation}
                    setEnableObfuscation={setEnableObfuscation}
                />
            ) : (
                <BinaryHashToggleCard 
                    enableBinaryHash={enableBinaryHash}
                    setEnableBinaryHash={setEnableBinaryHash}
                />
            )}

            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4">Advanced Configuration</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="row-span-2 bg-white/5 rounded-2xl border border-white/10 p-6 hover:border-white/20 transition-all flex flex-col gap-4">
                    <div className="flex items-center gap-3 mb-1">
                        <Cpu size={18} className="text-amber-400" />
                        <h4 className="font-bold text-white">Build Engine</h4>
                    </div>

                    {isNodeJS && (
                         <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-500 uppercase">Node Target</label>
                            <select
                                value={nodeTarget}
                                onChange={(e) => setNodeTarget(e.target.value)}
                                className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500/50"
                            >
                                <option value="node20-win-x64">Windows x64 (Node 20 LTS)</option>
                                <option value="node20-linux-x64">Linux x64 (Node 20 LTS)</option>
                                <option value="node22-win-x64">Windows x64 (Node 22)</option>
                                <option value="node22-linux-x64">Linux x64 (Node 22)</option>
                            </select>
                        </div>
                    )}

                    <div className="space-y-3 mt-2">
                        {isNodeJS && (
                             <div className="flex items-center justify-between p-3 bg-black/20 rounded-xl">
                                <span className="text-sm text-slate-300">Obfuscation</span>
                                <input
                                    type="checkbox"
                                    checked={enableObfuscation}
                                    onChange={toggleObfuscation}
                                    className="w-4 h-4 rounded border-slate-600 text-amber-500 focus:ring-amber-500 bg-transparent"
                                />
                            </div>
                        )}

                        <div className="flex items-center justify-between p-3 bg-black/20 rounded-xl">
                            <div className="flex flex-col">
                                <span className="text-sm text-slate-300">Fast Build</span>
                                <span className="text-[10px] text-slate-500">Skips onefile compression</span>
                            </div>
                            <input
                                type="checkbox"
                                checked={fastBuild}
                                onChange={toggleFastBuild}
                                className="w-4 h-4 rounded border-slate-600 text-amber-500 focus:ring-amber-500 bg-transparent"
                            />
                        </div>

                        <div className="flex items-center justify-between p-3 bg-black/20 rounded-xl">
                             <div className="flex flex-col">
                                <span className="text-sm text-slate-300">Offline Lease</span>
                                <span className="text-[10px] text-slate-500">24h offline access</span>
                            </div>
                            <input
                                type="checkbox"
                                checked={enableLease}
                                onChange={toggleLease}
                                className="w-4 h-4 rounded border-slate-600 text-amber-500 focus:ring-amber-500 bg-transparent"
                            />
                        </div>
                    </div>
                </div>

                <div className="bg-white/5 rounded-2xl border border-white/10 p-6 hover:border-white/20 transition-all flex flex-col gap-4">
                    <div className="flex items-center gap-3 mb-1">
                        <Layers size={18} className="text-purple-400" />
                        <h4 className="font-bold text-white">Assets</h4>
                    </div>

                    <div 
                        className={`
                            border-2 border-dashed rounded-xl p-4 flex items-center justify-center cursor-pointer transition-all
                            ${iconPath ? 'border-purple-500/50 bg-purple-500/5' : 'border-white/10 hover:border-purple-400/30 hover:bg-white/5'}
                        `}
                        onClick={browseIcon}
                    >
                        {iconPath ? (
                            <div className="flex items-center gap-3">
                                <Image size={24} className="text-purple-400" />
                                <div className="text-left overflow-hidden">
                                    <p className="text-sm font-medium text-white truncate max-w-[150px]">
                                        {iconPath.split(/[/\\]/).pop()}
                                    </p>
                                    <p className="text-xs text-slate-500">Click to change</p>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center">
                                <p className="text-sm text-slate-400">Upload Icon</p>
                                <p className="text-[10px] text-slate-600">.ico or .png</p>
                            </div>
                        )}
                    </div>
                </div>

                <div className="bg-white/5 rounded-2xl border border-white/10 p-6 hover:border-white/20 transition-all flex flex-col gap-4">
                     <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-3">
                            <Lock size={18} className="text-emerald-400" />
                            <h4 className="font-bold text-white">Environment</h4>
                        </div>
                        <span className="text-xs px-2 py-0.5 bg-white/10 rounded-full text-slate-400">
                            {selectedEnvKeys.length} baked
                        </span>
                    </div>

                    <div className="flex-1 bg-black/20 rounded-xl p-2 max-h-40 overflow-y-auto custom-scrollbar border border-white/5">
                        {Object.keys(envValues).length > 0 ? (
                            <div className="space-y-1">
                                {Object.entries(envValues).map(([key]) => (
                                    <label key={key} className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-lg cursor-pointer transition-colors group">
                                        <input
                                            type="checkbox"
                                            checked={selectedEnvKeys.includes(key)}
                                            onChange={(e) => handleEnvVarChange(key, e.target.checked)}
                                            className="w-3.5 h-3.5 rounded border-slate-600 text-emerald-500 focus:ring-emerald-500 bg-transparent"
                                        />
                                        <span className={`text-xs font-mono truncate transition-colors ${selectedEnvKeys.includes(key) ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-300'}`}>
                                            {key}
                                        </span>
                                    </label>
                                ))}
                            </div>
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-slate-600 text-xs text-center p-4">
                                <p>No .env file found</p>
                            </div>
                        )}
                    </div>
                </div>

                 <div className="md:col-span-2 lg:col-span-2 bg-white/5 rounded-2xl border border-white/10 p-6 hover:border-white/20 transition-all flex flex-col gap-4">
                    <div className="flex items-center gap-3 mb-1">
                        <Box size={18} className="text-blue-400" />
                        <h4 className="font-bold text-white">Dependencies & Data</h4>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                             <label className="text-xs font-semibold text-slate-500 uppercase mb-2 block">Include Packages</label>
                             <input 
                                type="text" 
                                placeholder="e.g. numpy, pandas" 
                                className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500/50"
                                value={includePackages.join(', ')}
                                onChange={(e) => handleIncludeChange(e.target.value)}
                            />
                        </div>
                        <div>
                             <label className="text-xs font-semibold text-slate-500 uppercase mb-2 block">Exclude Packages</label>
                             <input 
                                type="text" 
                                placeholder="e.g. tkinter" 
                                className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50"
                                value={excludePackages.join(', ')}
                                onChange={(e) => handleExcludeChange(e.target.value)}
                            />
                        </div>
                    </div>
                    
                    {detectedDataFolders.length > 0 && (
                        <div className="mt-2 pt-4 border-t border-white/5">
                            <label className="text-xs font-semibold text-slate-500 uppercase mb-2 block">Data Folders</label>
                             <div className="flex flex-wrap gap-2">
                                {detectedDataFolders.map(folder => (
                                    <label
                                        key={folder}
                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer transition-all border ${selectedDataFolders.includes(folder)
                                            ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                                            : 'bg-black/20 text-slate-400 border-white/5 hover:bg-white/5'
                                            }`}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={selectedDataFolders.includes(folder)}
                                            onChange={(e) => handleDataFolderChange(folder, e.target.checked)}
                                            className="hidden"
                                        />
                                        <FolderOpen size={12} />
                                        <span className="text-xs">{folder}/</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

            </div>

             {!entryFile && (
                <div className="flex items-center gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl animate-pulse">
                    <AlertCircle size={20} className="text-amber-500" />
                    <span className="text-amber-200 font-medium">Please select an entry point to proceed.</span>
                </div>
            )}
        </div>
    );
});

const ObfuscationToggleCard: React.FC<any> = memo(({ enableObfuscation, setEnableObfuscation }) => {
    const { tier } = usePricing();
    const isPro = tier !== 'free';
    
    const handleToggle = useCallback(() => {
        if (isPro) {
            setEnableObfuscation(!enableObfuscation);
        }
    }, [isPro, enableObfuscation, setEnableObfuscation]);

    const handleUpgrade = useCallback(() => {
        window.open('/pricing', '_blank');
    }, []);

    return (
        <div className={`relative overflow-hidden rounded-2xl border-2 mb-8 transition-all duration-300 ${
            enableObfuscation && isPro 
                ? 'bg-gradient-to-r from-purple-900/40 to-indigo-900/40 border-purple-500/50 shadow-lg shadow-purple-500/20' 
                : 'bg-white/5 border-white/10 hover:border-white/20'
        }`}>
            {isPro && enableObfuscation && (
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-indigo-500/10 animate-pulse" />
            )}
            
            <div className="relative z-10 p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${
                            enableObfuscation && isPro
                                ? 'bg-gradient-to-br from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/30'
                                : 'bg-white/10 text-slate-400'
                        }`}>
                            <Shield size={28} />
                        </div>
                        
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="font-bold text-white text-lg">Advanced Obfuscation</h3>
                                {!isPro && (
                                    <span className="px-2 py-0.5 bg-gradient-to-r from-purple-500 to-indigo-500 text-white text-xs font-bold rounded-full flex items-center gap-1">
                                        <Sparkles size={10} />
                                        PRO
                                    </span>
                                )}
                            </div>
                            <p className="text-sm text-slate-400 max-w-lg">
                                {isPro 
                                    ? 'Protect your source code with advanced obfuscation techniques.'
                                    : 'Upgrade to Pro to enable advanced code obfuscation.'
                                }
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {!isPro ? (
                            <button
                                onClick={handleUpgrade}
                                className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-xl transition-all hover:scale-105 flex items-center gap-2"
                            >
                                <Sparkles size={16} />
                                Upgrade to Pro
                            </button>
                        ) : (
                            <label className="flex items-center gap-3 cursor-pointer select-none">
                                <span className={`text-sm font-medium ${enableObfuscation ? 'text-purple-400' : 'text-slate-500'}`}>
                                    {enableObfuscation ? 'Enabled' : 'Disabled'}
                                </span>
                                <div 
                                    onClick={handleToggle}
                                    className={`w-16 h-9 rounded-full p-1 transition-colors duration-300 cursor-pointer ${
                                        enableObfuscation ? 'bg-purple-600' : 'bg-slate-700'
                                    }`}
                                >
                                    <div className={`w-7 h-7 rounded-full bg-white shadow-sm transition-transform duration-300 ${
                                        enableObfuscation ? 'translate-x-7' : 'translate-x-0'
                                    }`} />
                                </div>
                            </label>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
});

ObfuscationToggleCard.displayName = 'ObfuscationToggleCard';

const BinaryHashToggleCard: React.FC<any> = memo(({ enableBinaryHash, setEnableBinaryHash }) => {
    const handleToggle = useCallback(() => {
        setEnableBinaryHash(!enableBinaryHash);
    }, [enableBinaryHash, setEnableBinaryHash]);

    return (
        <div className={`relative overflow-hidden rounded-2xl border-2 mb-8 transition-all duration-300 ${
            enableBinaryHash 
                ? 'bg-gradient-to-r from-cyan-900/40 to-blue-900/40 border-cyan-500/50 shadow-lg shadow-cyan-500/20' 
                : 'bg-white/5 border-white/10 hover:border-white/20'
        }`}>
            {enableBinaryHash && (
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 animate-pulse" />
            )}
            
            <div className="relative z-10 p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center transition-all ${
                            enableBinaryHash
                                ? 'bg-gradient-to-br from-cyan-500 to-blue-600 text-white shadow-lg shadow-cyan-500/30'
                                : 'bg-white/10 text-slate-400'
                        }`}>
                            <Fingerprint size={28} />
                        </div>
                        
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="font-bold text-white text-lg">Binary Integrity Verification</h3>
                                <span className="px-2 py-0.5 bg-cyan-500/20 text-cyan-300 text-xs font-bold rounded-full">
                                    PYTHON
                                </span>
                            </div>
                            <p className="text-sm text-slate-400 max-w-lg">
                                Detect if your executable has been tampered with or modified after compilation.
                            </p>
                        </div>
                    </div>

                    <label className="flex items-center gap-3 cursor-pointer select-none">
                        <span className={`text-sm font-medium ${enableBinaryHash ? 'text-cyan-400' : 'text-slate-500'}`}>
                            {enableBinaryHash ? 'Enabled' : 'Disabled'}
                        </span>
                        <div 
                            onClick={handleToggle}
                            className={`w-16 h-9 rounded-full p-1 transition-colors duration-300 cursor-pointer ${
                                enableBinaryHash ? 'bg-cyan-600' : 'bg-slate-700'
                            }`}
                        >
                            <div className={`w-7 h-7 rounded-full bg-white shadow-sm transition-transform duration-300 ${
                                enableBinaryHash ? 'translate-x-7' : 'translate-x-0'
                            }`} />
                        </div>
                    </label>
                </div>
            </div>
        </div>
    );
});

BinaryHashToggleCard.displayName = 'BinaryHashToggleCard';

Step3Configure.displayName = 'Step3Configure';

export default Step3Configure;

import React, { useState } from 'react';
import { Settings, FileCode, Terminal, ChevronDown, ChevronUp, CheckCircle, AlertCircle, Lock, Palette, Package, FolderOpen, Image } from 'lucide-react';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

/**
 * Step3Configure - Configure build settings
 * Entry point selection, console mode, advanced options with env vars, icon, packages, data folders
 */
const Step3Configure = ({
    fileTree,
    files = [],
    entryFile,
    setEntryFile,
    entryPointCandidates = [],
    showConsole,
    setShowConsole,
    // Advanced Options props
    projectPath,
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
    // Obfuscation props
    enableObfuscation = false,
    setEnableObfuscation
}) => {
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [iconDragOver, setIconDragOver] = useState(false);

    // Check project language
    const isNodeJS = project?.language === 'nodejs';

    // Get available source files
    const sourceFiles = fileTree
        ? fileTree.files.filter(f => isNodeJS ? /\.(js|ts|mjs|cjs)$/.test(f) : f.endsWith('.py'))
        : files.filter(f => isNodeJS ? /\.(js|ts|mjs|cjs)$/.test(f.original_filename) : f.original_filename.endsWith('.py')).map(f => f.original_filename);

    const getCandidate = (file) => {
        return entryPointCandidates.find(c => c.file === file);
    };

    // Handle icon drop - Note: Drag & drop file paths are unreliable in Tauri v2
    // We still catch the drop but prompt user to use the browse dialog
    const handleIconDrop = async (e) => {
        e.preventDefault();
        setIconDragOver(false);

        // In Tauri, DataTransfer doesn't reliably expose full file paths
        // So we prompt the user to use the browse dialog instead
        if (e.dataTransfer.files?.length > 0) {
            // Show a message via the browseIcon dialog instead
            browseIcon();
        }
    };

    // Browse for icon file
    const browseIcon = async () => {
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

            if (selected) {
                // If PNG, convert to ICO
                if (selected.toLowerCase().endsWith('.png')) {
                    try {
                        const { invoke } = await import('@tauri-apps/api/core');
                        const icoPath = await invoke('convert_png_to_ico', { pngPath: selected });
                        setIconPath(icoPath);
                    } catch (err) {
                        console.error('PNG to ICO conversion failed:', err);
                        // Use PNG anyway - Nuitka can handle it
                        setIconPath(selected);
                    }
                } else {
                    setIconPath(selected);
                }
            }
        } catch (error) {
            console.error('Failed to open file picker:', error);
        }
    };

    return (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white mb-2">Configure Build</h2>
                <p className="text-slate-400 text-sm">
                    Set the entry point and build options for your executable
                </p>
            </div>

            {/* Entry Point Selection */}
            <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 rounded-xl border border-emerald-500/20 p-5">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <FileCode size={20} className="text-emerald-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Entry Point</h3>
                        <p className="text-xs text-slate-400">The main {isNodeJS ? 'Javascript/Node' : 'Python'} file to run</p>
                    </div>
                </div>

                <select
                    value={entryFile}
                    onChange={(e) => setEntryFile(e.target.value)}
                    className="input w-full text-base py-3 mb-3"
                >
                    <option value="">Select entry file...</option>
                    {sourceFiles.map((file, idx) => {
                        const candidate = getCandidate(file);
                        return (
                            <option key={idx} value={file}>
                                {file} {candidate?.score > 0 ? `(score: ${candidate.score})` : ''}
                            </option>
                        );
                    })}
                </select>

                {/* Candidates info */}
                {entryPointCandidates.length > 0 && (
                    <div className="text-xs text-slate-400 space-y-1">
                        <p className="font-medium text-slate-300 mb-2">Top candidates detected:</p>
                        {entryPointCandidates.slice(0, 3).map((candidate, i) => (
                            <div
                                key={i}
                                className={`flex items-center justify-between p-2 rounded ${candidate.file === entryFile
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : 'bg-white/5'
                                    }`}
                            >
                                <span className="font-mono">{candidate.file}</span>
                                <span className="text-slate-500">{candidate.reason}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Console Mode */}
            <div className="bg-white/5 rounded-xl border border-white/10 p-5">
                <label className="flex items-center gap-4 cursor-pointer">
                    <div className="w-10 h-10 rounded-full bg-slate-500/20 flex items-center justify-center">
                        <Terminal size={20} className="text-slate-400" />
                    </div>
                    <div className="flex-1">
                        <h3 className="font-semibold text-white">Show Console Window</h3>
                        <p className="text-xs text-slate-400">Enable for apps with print() output</p>
                    </div>
                    <div className={`w-12 h-6 rounded-full p-1 transition-colors ${showConsole ? 'bg-emerald-500' : 'bg-slate-600'
                        }`}>
                        <div className={`w-4 h-4 rounded-full bg-white transition-transform ${showConsole ? 'translate-x-6' : 'translate-x-0'
                            }`} />
                    </div>
                    <input
                        type="checkbox"
                        checked={showConsole}
                        onChange={(e) => setShowConsole(e.target.checked)}
                        className="hidden"
                    />
                </label>
            </div>

            {/* Advanced Options */}
            <div className="bg-white/5 rounded-xl border border-white/10 overflow-hidden">
                <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
                >
                    <div className="flex items-center gap-3">
                        <Settings size={18} className="text-slate-400" />
                        <span className="font-medium text-white">Advanced Options</span>
                        {(selectedEnvKeys.length > 0 || iconPath || includePackages.length > 0 || excludePackages.length > 0 || selectedDataFolders.length > 0) && (
                            <span className="text-xs bg-indigo-500/30 text-indigo-300 px-2 py-0.5 rounded-full">
                                {[
                                    selectedEnvKeys.length > 0 && `${selectedEnvKeys.length} env`,
                                    iconPath && 'icon',
                                    includePackages.length > 0 && 'packages',
                                    selectedDataFolders.length > 0 && 'data'
                                ].filter(Boolean).join(', ')}
                            </span>
                        )}
                    </div>
                    {showAdvanced ? (
                        <ChevronUp size={18} className="text-slate-400" />
                    ) : (
                        <ChevronDown size={18} className="text-slate-400" />
                    )}
                </button>

                {showAdvanced && (
                    <div className="p-4 border-t border-white/10 space-y-6">

                        {/* Node.js Specific Options */}
                        {isNodeJS && (
                            <div className="space-y-4">
                                <div className="space-y-3">
                                    <div className="flex items-center gap-2">
                                        <Terminal size={16} className="text-yellow-400" />
                                        <label className="text-sm font-medium text-white">Target Platform</label>
                                    </div>
                                    <select
                                        value={nodeTarget}
                                        onChange={(e) => setNodeTarget(e.target.value)}
                                        className="input w-full text-sm"
                                    >
                                        <option value="node16-win-x64">Windows x64 (Node 16)</option>
                                        <option value="node18-win-x64">Windows x64 (Node 18)</option>
                                        <option value="node20-win-x64">Windows x64 (Node 20)</option>
                                        <option value="node16-linux-x64">Linux x64 (Node 16)</option>
                                        <option value="node18-linux-x64">Linux x64 (Node 18)</option>
                                        <option value="node20-linux-x64">Linux x64 (Node 20)</option>
                                        <option value="node16-macos-x64">macOS x64 (Node 16)</option>
                                        <option value="node18-macos-x64">macOS x64 (Node 18)</option>
                                        <option value="node20-macos-x64">macOS x64 (Node 20)</option>
                                    </select>
                                    <p className="text-xs text-slate-500">
                                        The "pkg" tool will bundle your code into a standalone executable for this platform.
                                    </p>
                                </div>

                                {/* Obfuscation Toggle - Default OFF for faster builds */}
                                <div className="bg-white/5 rounded-lg p-3">
                                    <label className="flex items-center gap-3 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={enableObfuscation}
                                            onChange={(e) => setEnableObfuscation?.(e.target.checked)}
                                            className="w-4 h-4 rounded border-slate-500 text-purple-500 focus:ring-purple-500"
                                        />
                                        <div className="flex-1">
                                            <span className="text-sm font-medium text-white">Enable Code Obfuscation</span>
                                            <p className="text-xs text-slate-500">Makes code harder to reverse-engineer (slower build)</p>
                                        </div>
                                        {enableObfuscation && (
                                            <span className="text-xs bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded">
                                                Enabled
                                            </span>
                                        )}
                                    </label>
                                </div>
                            </div>
                        )}


                        {/* Python/Nuitka Specific Options */}
                        {!isNodeJS && (
                            <>
                                {/* 1. Environment Variables */}
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <Lock size={16} className="text-emerald-400" />
                                            <label className="text-sm font-medium text-white">
                                                Bake Environment Variables
                                            </label>
                                        </div>
                                        <span className="text-xs text-slate-400">
                                            {selectedEnvKeys.length} selected
                                        </span>
                                    </div>
                                    {Object.keys(envValues).length > 0 ? (
                                        <div className="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
                                            {Object.entries(envValues).map(([key, value]) => (
                                                <label key={key} className="flex items-center gap-3 p-2 bg-white/5 rounded-lg cursor-pointer hover:bg-white/10 transition-colors">
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedEnvKeys.includes(key)}
                                                        onChange={(e) => {
                                                            if (e.target.checked) {
                                                                setSelectedEnvKeys([...selectedEnvKeys, key]);
                                                            } else {
                                                                setSelectedEnvKeys(selectedEnvKeys.filter(k => k !== key));
                                                            }
                                                        }}
                                                        className="w-4 h-4 rounded border-slate-500 text-emerald-500 focus:ring-emerald-500"
                                                    />
                                                    <span className="font-mono text-sm text-emerald-400">{key}</span>
                                                    <span className="text-xs text-slate-500">= ••••••</span>
                                                </label>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-xs text-slate-500 italic">
                                            {projectPath ? 'No .env file detected in project' : 'Select a project folder to detect .env variables'}
                                        </p>
                                    )}
                                </div>

                                {/* 2. Custom Icon */}
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <Palette size={16} className="text-purple-400" />
                                        <label className="text-sm font-medium text-white">Custom Icon</label>
                                    </div>
                                    <div
                                        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all ${iconDragOver
                                            ? 'border-indigo-500 bg-indigo-500/10'
                                            : iconPath
                                                ? 'border-emerald-500/50 bg-emerald-500/5'
                                                : 'border-white/20 hover:border-indigo-500/50'
                                            }`}
                                        onDrop={handleIconDrop}
                                        onDragOver={(e) => { e.preventDefault(); setIconDragOver(true); }}
                                        onDragLeave={() => setIconDragOver(false)}
                                        onClick={browseIcon}
                                    >
                                        {iconPath ? (
                                            <div className="flex items-center justify-center gap-2">
                                                <Image size={18} className="text-emerald-400" />
                                                <span className="text-emerald-400 text-sm">{iconPath.split(/[/\\]/).pop()}</span>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); setIconPath(null); }}
                                                    className="ml-2 text-slate-400 hover:text-red-400"
                                                >
                                                    ×
                                                </button>
                                            </div>
                                        ) : (
                                            <span className="text-slate-400 text-sm">
                                                Drop .ico/.png or click to browse
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-xs text-slate-500">PNG files are auto-converted to .ico</p>
                                </div>

                                {/* 3. Include/Exclude Packages */}
                                <div className="space-y-3">
                                    <div className="flex items-center gap-2">
                                        <Package size={16} className="text-blue-400" />
                                        <label className="text-sm font-medium text-white">Package Control</label>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs text-slate-400 mb-1 block">Include Packages</label>
                                            <input
                                                type="text"
                                                placeholder="package1, package2"
                                                className="input w-full text-sm"
                                                value={includePackages.join(', ')}
                                                onChange={(e) => setIncludePackages(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-slate-400 mb-1 block">Exclude Packages</label>
                                            <input
                                                type="text"
                                                placeholder="tkinter, test"
                                                className="input w-full text-sm"
                                                value={excludePackages.join(', ')}
                                                onChange={(e) => setExcludePackages(e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* 4. Data Folders */}
                                {detectedDataFolders.length > 0 && (
                                    <div className="space-y-3">
                                        <div className="flex items-center gap-2">
                                            <FolderOpen size={16} className="text-amber-400" />
                                            <label className="text-sm font-medium text-white">Bundle Data Folders</label>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {detectedDataFolders.map(folder => (
                                                <label
                                                    key={folder}
                                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full cursor-pointer transition-colors ${selectedDataFolders.includes(folder)
                                                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                                        : 'bg-white/5 text-slate-400 border border-transparent hover:bg-white/10'
                                                        }`}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedDataFolders.includes(folder)}
                                                        onChange={(e) => {
                                                            if (e.target.checked) {
                                                                setSelectedDataFolders([...selectedDataFolders, folder]);
                                                            } else {
                                                                setSelectedDataFolders(selectedDataFolders.filter(f => f !== folder));
                                                            }
                                                        }}
                                                        className="hidden"
                                                    />
                                                    <span className="text-sm">{folder}/</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Tip */}
                                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                                    <p className="text-xs text-blue-400">
                                        💡 The executable will include all dependencies from your requirements.txt automatically.
                                    </p>
                                </div>
                            </>
                        )}
                    </div>
                )}
            </div>

            {/* Validation */}
            {!entryFile && (
                <div className="flex items-center gap-2 text-amber-400 text-sm">
                    <AlertCircle size={16} />
                    <span>Please select an entry file to continue</span>
                </div>
            )}

            {entryFile && (
                <div className="flex items-center gap-2 text-emerald-400 text-sm">
                    <CheckCircle size={16} />
                    <span>Configuration complete - ready for next step</span>
                </div>
            )}
        </div>
    );
};

export default Step3Configure;

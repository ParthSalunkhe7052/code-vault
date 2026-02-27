import React, { useState, useEffect } from 'react';
import { Loader, Hammer, FolderOpen, CheckCircle, XCircle, AlertCircle, Download, Settings, ChevronDown, ChevronUp, FileText, Lock } from 'lucide-react';
import { auth } from '../../services/api';
import { useToast } from '../Toast';
import { Project, License } from '../../types/api';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__ !== undefined;

interface DirectBuildSectionProps {
    project: Project | null;
    licenses?: License[];
    entryFile?: string;
    onBuildStart: (options: any) => void;
    hasUploadedFiles?: boolean;
    serverUrl?: string;
}

const DirectBuildSection: React.FC<DirectBuildSectionProps> = ({
    project,
    licenses = [],
    entryFile,
    onBuildStart,
    hasUploadedFiles = false,
    serverUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
}) => {
    const toast = useToast();
    const [selectedLicense, setSelectedLicense] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [projectPath, setProjectPath] = useState('');
    const [showConsole, setShowConsole] = useState(true);

    const [bundleRequirements, setBundleRequirements] = useState(true);
    const [bakeEnvValues, setBakeEnvValues] = useState(true);
    const [envValues, setEnvValues] = useState<Record<string, string>>({});
    const [showEnvEditor, setShowEnvEditor] = useState(false);
    const [frontendHandling, setFrontendHandling] = useState('skip');

    const [projectStructure, setProjectStructure] = useState<any>(null);
    const [scanningStructure, setScanningStructure] = useState(false);

    const [downloading, setDownloading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState(0);
    const [downloadedPath, setDownloadedPath] = useState<string | null>(null);

    const [prerequisites, setPrerequisites] = useState<{
        checking: boolean;
        python: string | null;
        nuitka: string | null;
        node: string | null;
        npm: string | null;
        pkg: string | null;
        allReady: boolean;
        error?: string;
    }>({
        checking: true,
        python: null,
        nuitka: null,
        node: null,
        npm: null,
        pkg: null,
        allReady: false
    });

    const isNodeJS = project?.language === 'nodejs';
    const activeLicenses = licenses.filter(l => l.status === 'active');

    useEffect(() => {
        checkPrerequisites();
    }, []);

    useEffect(() => {
        if (projectPath && isTauri) {
            scanProjectStructure(projectPath);
        }
    }, [projectPath]);

    const checkPrerequisites = async () => {
        if (!isTauri) {
            setPrerequisites({
                checking: false,
                python: null,
                nuitka: null,
                node: null,
                npm: null,
                pkg: null,
                allReady: false,
                error: 'Build only available in desktop app'
            });
            return;
        }

        try {
            const { invoke } = await import('@tauri-apps/api/core');

            if (isNodeJS) {
                let nodeVersion: string | null = null;
                let npmVersion: string | null = null;
                let pkgVersion: string | null = null;

                try {
                    const nodeStatus = await invoke('check_node_installed') as { installed: boolean; version?: string };
                    nodeVersion = nodeStatus.installed ? nodeStatus.version || 'Installed' : null;
                } catch (_e) {
                    nodeVersion = null;
                }

                try {
                    const npmStatus = await invoke('check_npm_installed') as { installed: boolean; version?: string };
                    npmVersion = npmStatus.installed ? npmStatus.version || 'Installed' : null;
                } catch (_e) {
                    npmVersion = null;
                }

                try {
                    const pkgStatus = await invoke('check_pkg_installed') as { installed: boolean; version?: string };
                    pkgVersion = pkgStatus.installed ? (pkgStatus.version || 'via npx') : null;
                } catch (_e) {
                    pkgVersion = null;
                }

                setPrerequisites({
                    checking: false,
                    python: null,
                    nuitka: null,
                    node: nodeVersion,
                    npm: npmVersion,
                    pkg: pkgVersion,
                    allReady: nodeVersion !== null && pkgVersion !== null
                });
            } else {
                let nuitkaVersion: string | null = null;
                let pythonOk = false;

                try {
                    nuitkaVersion = await invoke('get_nuitka_version') as string;
                    pythonOk = true;
                } catch (_e) {
                    try {
                        await invoke('check_nuitka_installed');
                        pythonOk = true;
                    } catch (_e2) {
                        pythonOk = false;
                    }
                }

                setPrerequisites({
                    checking: false,
                    python: pythonOk ? 'Installed' : null,
                    nuitka: nuitkaVersion,
                    node: null,
                    npm: null,
                    pkg: null,
                    allReady: pythonOk && nuitkaVersion !== null
                });
            }
        } catch (error: any) {
            setPrerequisites({
                checking: false,
                python: null,
                nuitka: null,
                node: null,
                npm: null,
                pkg: null,
                allReady: false,
                error: error.toString()
            });
        }
    };

    const scanProjectStructure = async (path: string) => {
        if (!isTauri) return;

        setScanningStructure(true);
        try {
            const { invoke } = await import('@tauri-apps/api/core');
            const structure = await invoke('scan_project_structure', { projectPath: path }) as any;
            setProjectStructure(structure);

            if (structure.has_frontend) {
                setFrontendHandling('separate');
            }

            if (structure.has_env && bakeEnvValues) {
                try {
                    const envVals = await invoke('read_env_file_values', { projectPath: path }) as Record<string, string>;
                    setEnvValues(envVals);
                } catch (_e) {
                    console.error('Failed to read .env:', _e);
                }
            }
        } catch (error) {
            console.error('Failed to scan project:', error);
        } finally {
            setScanningStructure(false);
        }
    };

    const handleBrowseOutput = async () => {
        if (!isTauri) return;

        try {
            const { open } = await import('@tauri-apps/plugin-dialog');
            const selected = await open({
                directory: true,
                multiple: false,
                title: 'Select Output Folder'
            });

            if (selected && typeof selected === 'string') {
                setOutputDir(selected);
            }
        } catch (error) {
            console.error('Failed to open folder picker:', error);
        }
    };

    const handleBrowseProject = async () => {
        if (!isTauri) return;

        try {
            const { open } = await import('@tauri-apps/plugin-dialog');
            const selected = await open({
                directory: true,
                multiple: false,
                title: `Select Project Folder (where your ${project?.language === 'nodejs' ? '.js' : '.py'} files are)`
            });

            if (selected && typeof selected === 'string') {
                setProjectPath(selected);
            }
        } catch (error) {
            console.error('Failed to open folder picker:', error);
        }
    };

    const handleDownloadAndBuild = async () => {
        if (!isTauri || !project?.id) return;

        setDownloading(true);
        setDownloadProgress(0);

        try {
            const { invoke } = await import('@tauri-apps/api/core');
            const { listen } = await import('@tauri-apps/api/event');

            const unlisten = await listen('download-progress', (event: any) => {
                const { progress } = event.payload;
                setDownloadProgress(progress);
            });

            const extractedPath = await invoke('download_and_prepare_for_compile', {
                projectId: project.id,
                serverUrl: serverUrl,
                authToken: auth.getToken() || '',
                targetDir: null
            }) as string;

            unlisten();
            setDownloadedPath(extractedPath);
            setProjectPath(extractedPath);
            setDownloading(false);

        } catch (error) {
            setDownloading(false);
            toast.error(`Download failed: ${error}`);
        }
    };

    const handleBuild = () => {
        if (!entryFile) {
            toast.warning('Please select an entry file first');
            return;
        }

        if (!prerequisites.allReady) {
            toast.warning('Please ensure Python and Nuitka are installed');
            return;
        }

        onBuildStart({
            projectPath: projectPath,
            licenseKey: selectedLicense || null,
            outputDir: outputDir || null,
            entryFile,
            showConsole: showConsole,
            bundleRequirements: bundleRequirements,
            envValues: bakeEnvValues ? envValues : null,
            buildFrontend: frontendHandling !== 'skip',
            splitFrontend: frontendHandling === 'separate',
            createLauncher: frontendHandling !== 'skip' || true
        });
    };

    const canBuild = !!(projectPath && entryFile && prerequisites.allReady);

    return (
        <div className="space-y-5">
            {hasUploadedFiles && (
                <div className="bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-xl p-5 border border-green-500/20">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                            <Download size={20} className="text-green-400" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-white">Download from Server</h3>
                            <p className="text-xs text-slate-400">Download uploaded files and compile locally</p>
                        </div>
                    </div>

                    {downloadedPath ? (
                        <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                            <p className="text-sm text-green-300">
                                <CheckCircle size={16} className="inline mr-2" />
                                Files downloaded to: <code className="bg-white/10 px-1.5 py-0.5 rounded text-xs">{downloadedPath}</code>
                            </p>
                        </div>
                    ) : downloading ? (
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-slate-300">
                                <Loader size={16} className="animate-spin" />
                                <span>Downloading project files... {downloadProgress}%</span>
                            </div>
                            <div className="w-full bg-white/10 rounded-full h-2">
                                <div
                                    className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full transition-all"
                                    style={{ width: `${downloadProgress}%` }}
                                />
                            </div>
                        </div>
                    ) : (
                        <button
                            onClick={handleDownloadAndBuild}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-medium hover:from-green-500 hover:to-emerald-500 transition-all"
                        >
                            <Download size={18} />
                            Download & Prepare for Build
                        </button>
                    )}
                </div>
            )}

            <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 rounded-xl p-5 border border-amber-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                        <span className="text-lg font-bold text-amber-400">0</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Local Project Folder</h3>
                        <p className="text-xs text-slate-400">Select the folder on your computer containing the {project?.language === 'nodejs' ? 'JavaScript' : 'Python'} files</p>
                    </div>
                </div>

                {hasUploadedFiles && !downloadedPath && (
                    <div className="mb-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                        <p className="text-xs text-blue-300">
                            <strong>Tip:</strong> Use &quot;Download &amp; Prepare for Build&quot; above to get your server files, or select a local folder here.
                        </p>
                    </div>
                )}

                <div className="flex gap-2">
                    <input
                        type="text"
                        value={projectPath}
                        onChange={(e) => setProjectPath(e.target.value)}
                        placeholder="Browse to select your local project folder..."
                        className="input flex-1 text-sm py-2.5"
                    />
                    <button
                        onClick={handleBrowseProject}
                        className="px-4 py-2.5 bg-amber-500/20 hover:bg-amber-500/30 rounded-lg text-amber-400 transition-colors flex items-center gap-2"
                    >
                        <FolderOpen size={16} />
                        Browse
                    </button>
                </div>

                {scanningStructure && (
                    <div className="mt-3 flex items-center gap-2 text-slate-400 text-sm">
                        <Loader size={14} className="animate-spin" />
                        Scanning project structure...
                    </div>
                )}
                {projectStructure && (
                    <div className="mt-3 p-3 bg-white/5 rounded-lg border border-white/10 text-xs space-y-1">
                        <p className="text-slate-300">
                            <strong>Detected:</strong> {projectStructure.packages?.length || 0} packages, {projectStructure.data_dirs?.length || 0} data dirs
                        </p>
                        {projectStructure.has_requirements && (
                            <p className="text-emerald-400">✓ requirements.txt found</p>
                        )}
                        {projectStructure.has_env && (
                            <p className="text-emerald-400">✓ .env file found ({projectStructure.env_keys?.length || 0} keys)</p>
                        )}
                        {projectStructure.has_frontend && (
                            <p className="text-cyan-400">✓ Frontend detected: {projectStructure.frontend_framework}</p>
                        )}
                    </div>
                )}
            </div>

            <div className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-xl p-5 border border-purple-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                        <span className="text-lg font-bold text-purple-400">1</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Select License</h3>
                        <p className="text-xs text-slate-400">Embed license protection in your build</p>
                    </div>
                </div>

                {activeLicenses.length > 0 ? (
                    <select
                        value={selectedLicense}
                        onChange={(e) => setSelectedLicense(e.target.value)}
                        className="input w-full text-base py-3"
                    >
                        <option value="">No license (Demo mode)</option>
                        {activeLicenses.map(lic => (
                            <option key={lic.id} value={lic.license_key}>
                                {lic.license_key} {lic.client_name ? `- ${lic.client_name}` : ''}
                            </option>
                        ))}
                    </select>
                ) : (
                    <div className="text-sm text-slate-400 p-3 bg-white/5 rounded-lg border border-white/10">
                        No licenses created yet.{' '}
                        <a href="/licenses" className="text-indigo-400 hover:underline">
                            Create one →
                        </a>
                    </div>
                )}
            </div>

            <div className="bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-xl p-5 border border-blue-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <span className="text-lg font-bold text-blue-400">2</span>
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Output Location</h3>
                        <p className="text-xs text-slate-400">Where to save the compiled .exe</p>
                    </div>
                </div>

                <div className="flex gap-2">
                    <input
                        type="text"
                        value={outputDir}
                        onChange={(e) => setOutputDir(e.target.value)}
                        placeholder="Default: Project folder"
                        className="input flex-1 text-sm py-2.5"
                    />
                    <button
                        onClick={handleBrowseOutput}
                        className="px-4 py-2.5 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors flex items-center gap-2"
                    >
                        <FolderOpen size={16} />
                        Browse
                    </button>
                </div>
            </div>

            <div className="bg-gradient-to-br from-slate-500/10 to-gray-500/10 rounded-xl p-5 border border-slate-500/20">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-slate-500/20 flex items-center justify-center">
                        <Settings size={18} className="text-slate-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Build Options</h3>
                        <p className="text-xs text-slate-400">Configure compilation settings</p>
                    </div>
                </div>

                <div className="space-y-3">
                    <label className="flex items-center gap-3 cursor-pointer p-3 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-colors">
                        <input
                            type="checkbox"
                            checked={showConsole}
                            onChange={(e) => setShowConsole(e.target.checked)}
                            className="w-5 h-5 rounded border-slate-500 bg-slate-800 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
                        />
                        <div className="flex-1">
                            <span className="text-white font-medium">Show Console Window</span>
                            <p className="text-xs text-slate-400">Enable for console apps with print() output</p>
                        </div>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer p-3 bg-white/5 rounded-lg border border-white/10 hover:bg-white/10 transition-colors">
                        <input
                            type="checkbox"
                            checked={bundleRequirements}
                            onChange={(e) => setBundleRequirements(e.target.checked)}
                            className="w-5 h-5 rounded border-slate-500 bg-slate-800 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
                        />
                        <div className="flex-1">
                            <div className="flex items-center gap-2">
                                <FileText size={16} className="text-blue-400" />
                                <span className="text-white font-medium">Bundle requirements.txt</span>
                            </div>
                            <p className="text-xs text-slate-400">Auto-install dependencies on first run (recommended)</p>
                        </div>
                    </label>

                    {projectStructure?.has_env && (
                        <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={bakeEnvValues}
                                    onChange={(e) => setBakeEnvValues(e.target.checked)}
                                    className="w-5 h-5 rounded border-slate-500 bg-slate-800 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
                                />
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <Lock size={16} className="text-amber-400" />
                                        <span className="text-white font-medium">Bake .env values into binary</span>
                                    </div>
                                    <p className="text-xs text-slate-400">Hardcode environment variables (most secure)</p>
                                </div>
                                <button
                                    onClick={() => setShowEnvEditor(!showEnvEditor)}
                                    className="p-1 hover:bg-white/10 rounded"
                                >
                                    {showEnvEditor ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                </button>
                            </label>

                            {showEnvEditor && bakeEnvValues && (
                                <div className="mt-3 space-y-2 pt-3 border-t border-white/10">
                                    {Object.entries(envValues).map(([key, value]) => (
                                        <div key={key} className="flex gap-2 items-center">
                                            <span className="text-xs text-slate-400 w-32 truncate">{key}</span>
                                            <input
                                                type="text"
                                                value={value}
                                                onChange={(e) => setEnvValues({ ...envValues, [key]: e.target.value })}
                                                className="input flex-1 text-xs py-1.5"
                                            />
                                        </div>
                                    ))}
                                    {Object.keys(envValues).length === 0 && (
                                        <p className="text-xs text-slate-500">No environment variables found in .env</p>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {projectStructure?.has_frontend && (
                        <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                            <label className="block text-white font-medium mb-2">
                                Frontend Handling ({projectStructure.frontend_framework})
                            </label>
                            <select
                                value={frontendHandling}
                                onChange={(e) => setFrontendHandling(e.target.value)}
                                className="input w-full text-sm py-2"
                            >
                                <option value="skip">Skip - Don&apos;t include frontend</option>
                                <option value="bundle">Bundle - Include as static files in backend</option>
                                <option value="separate">Separate - Create launcher for both (recommended)</option>
                            </select>
                            {frontendHandling === 'separate' && (
                                <p className="text-xs text-cyan-400 mt-2">
                                    Will create: backend.exe + frontend/ folder + launcher.bat
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                <h4 className="text-sm font-medium text-slate-400 mb-3">
                    Build Prerequisites {isNodeJS ? '(Node.js)' : '(Python)'}
                </h4>

                {prerequisites.checking ? (
                    <div className="flex items-center gap-2 text-slate-400">
                        <Loader size={16} className="animate-spin" />
                        <span className="text-sm">Checking prerequisites...</span>
                    </div>
                ) : prerequisites.error ? (
                    <div className="flex items-center gap-2 text-amber-400">
                        <AlertCircle size={16} />
                        <span className="text-sm">{prerequisites.error}</span>
                    </div>
                ) : isNodeJS ? (
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            {prerequisites.node ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-red-400" />
                            )}
                            <span className={`text-sm ${prerequisites.node ? 'text-emerald-400' : 'text-red-400'}`}>
                                Node.js {prerequisites.node || 'Not found'}
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            {prerequisites.pkg ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-red-400" />
                            )}
                            <span className={`text-sm ${prerequisites.pkg ? 'text-emerald-400' : 'text-red-400'}`}>
                                pkg {prerequisites.pkg || 'Not available'}
                            </span>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            {prerequisites.python ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-red-400" />
                            )}
                            <span className={`text-sm ${prerequisites.python ? 'text-emerald-400' : 'text-red-400'}`}>
                                Python {prerequisites.python || 'Not found'}
                            </span>
                        </div>
                        <div className="flex items-center gap-2">
                            {prerequisites.nuitka ? (
                                <CheckCircle size={16} className="text-emerald-400" />
                            ) : (
                                <XCircle size={16} className="text-red-400" />
                            )}
                            <span className={`text-sm ${prerequisites.nuitka ? 'text-emerald-400' : 'text-red-400'}`}>
                                Nuitka {prerequisites.nuitka || 'Not installed'}
                            </span>
                        </div>
                    </div>
                )}
            </div>

            <button
                onClick={handleBuild}
                disabled={!canBuild}
                className={`w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl font-semibold text-lg transition-all shadow-lg ${canBuild
                    ? 'bg-gradient-to-r from-emerald-600 to-cyan-600 text-white hover:from-emerald-500 hover:to-cyan-500 shadow-emerald-500/25'
                    : 'bg-gray-700 text-gray-400 cursor-not-allowed'
                    }`}
            >
                <Hammer size={22} />
                Build Project
            </button>
        </div>
    );
};

export default DirectBuildSection;

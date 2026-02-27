import React, { useState, useRef, useEffect, useCallback, memo, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import WizardSidebar from './WizardSidebar';
import { Step1Upload, Step2Review, Step3Configure, Step4License, Step5Build } from './WizardSteps';
import PrerequisitesCheck from '../PrerequisitesCheck';
import { useSettings } from '../../contexts/SettingsContext';
import { useProjectBuild } from '../../contexts/BuildContext';
import api from '../../services/api';
import WizardErrorBoundary from './WizardErrorBoundary';
import { Project, ProjectConfig, License } from '../../types/api';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__ !== undefined;

interface ProjectWizardProps {
    isOpen: boolean;
    onClose: () => void;
    project: Project | null;
    configLoading: boolean;
    configData: ProjectConfig & { tier?: string; is_pro?: boolean; can_remove_branding?: boolean; selected_license_id?: string; fast_build?: boolean };
    setConfigData: React.Dispatch<React.SetStateAction<any>>;
    uploadProgress: boolean;
    uploadPercent?: number;
    uploadStage?: string;
    onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onZipUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onDeleteFile: (fileId: string) => void;
    onConfigSave: (showNotification?: boolean) => Promise<void>;
    licenses?: License[];
}

const ProjectWizard: React.FC<ProjectWizardProps> = ({
    isOpen,
    onClose,
    project,
    configLoading,
    configData,
    setConfigData,
    uploadProgress,
    uploadPercent = 0,
    uploadStage = 'uploading',
    onFileUpload,
    onZipUpload,
    onDeleteFile,
    onConfigSave
}) => {
    const { settings } = useSettings();
    const navigate = useNavigate();

    const projectBuild = useProjectBuild(project?.id || '');
    const {
        status: buildStatus,
        progress: buildProgress,
        logs: buildLogs,
        outputPath,
        isBuilding,
        jobId: currentJobId
    } = projectBuild;

    const [currentStep, setCurrentStep] = useState(1);
    const [completedSteps, setCompletedSteps] = useState<number[]>([]);
    const [isDirty, setIsDirty] = useState(false);
    const [showQuickBuild, setShowQuickBuild] = useState(false);
    const [protectionMode, setProtectionMode] = useState('generic');
    const [showConsole, setShowConsole] = useState(true);
    const [projectPath, setProjectPath] = useState('');
    const [showPrereqs, setShowPrereqs] = useState(false);

    const [envValues, setEnvValues] = useState<Record<string, string>>({});
    const [selectedEnvKeys, setSelectedEnvKeys] = useState<string[]>([]);
    const [iconPath, setIconPath] = useState<string | null>(null);
    const [includePackages, setIncludePackages] = useState<string[]>([]);
    const [excludePackages, setExcludePackages] = useState<string[]>(settings.defaultExcludePackages || []);
    const [detectedDataFolders, setDetectedDataFolders] = useState<string[]>([]);
    const [selectedDataFolders, setSelectedDataFolders] = useState<string[]>([]);
    const [demoMode, setDemoMode] = useState(settings.defaultDemoEnabled || false);
    const [demoDuration, setDemoDuration] = useState(settings.defaultDemoDuration || 60);

    const [nodeTarget, setNodeTarget] = useState('node20-win-x64');
    const [enableObfuscation, setEnableObfuscation] = useState(false);
    const [enableLease, setEnableLease] = useState(false);
    const [fastBuild, setFastBuild] = useState(false);
    const [enableBinaryHash, setEnableBinaryHash] = useState(false);

    const [distributionType, setDistributionType] = useState(settings.defaultDistributionType || 'portable');
    const [createDesktopShortcut, setCreateDesktopShortcut] = useState(settings.defaultCreateDesktopShortcut ?? true);
    const [createStartMenu, setCreateStartMenu] = useState(settings.defaultCreateStartMenu ?? true);
    const [publisher, setPublisher] = useState(settings.defaultPublisher || '');

    useEffect(() => {
        if (isOpen) {
            const STORAGE_KEY = `codevault_wizard_${project?.id}`;
            const EXPIRY_MS = 24 * 60 * 60 * 1000;

            if (buildStatus === 'running' || buildStatus === 'pending') {
                setCurrentStep(5);
                setCompletedSteps([1, 2, 3, 4]);
            } else if (buildStatus === 'completed' || buildStatus === 'failed') {
                setCurrentStep(5);
                setCompletedSteps([1, 2, 3, 4]);
            } else {
                try {
                    const saved = localStorage.getItem(STORAGE_KEY);
                    if (saved) {
                        const state = JSON.parse(saved);
                        if (Date.now() - state.timestamp < EXPIRY_MS) {
                            setCurrentStep(state.currentStep || 1);
                            setCompletedSteps(state.completedSteps || []);
                            if (state.protectionMode) setProtectionMode(state.protectionMode);
                            if (state.projectPath) setProjectPath(state.projectPath);
                            return;
                        } else {
                            localStorage.removeItem(STORAGE_KEY);
                        }
                    }
                } catch (e) {
                    console.warn('[Wizard] Failed to restore state:', e);
                }

                const hasFiles = (configData.files || []).length > 0 || configData.settings?.file_tree;
                setCurrentStep(hasFiles ? 2 : 1);
                setCompletedSteps(hasFiles ? [1] : []);
            }

            if (configData.compiler_options?.target) {
                setNodeTarget(configData.compiler_options.target);
            }
        }
        return undefined;
    }, [isOpen, configData.files, configData.settings?.file_tree, buildStatus, project?.id, configData.compiler_options?.target]);

    useEffect(() => {
        if (isOpen && project?.id && currentStep > 1) {
            const STORAGE_KEY = `codevault_wizard_${project.id}`;
            const timeoutId = setTimeout(() => {
                try {
                    localStorage.setItem(STORAGE_KEY, JSON.stringify({
                        projectId: project.id,
                        currentStep,
                        completedSteps,
                        protectionMode,
                        projectPath,
                        timestamp: Date.now()
                    }));
                } catch (e) {
                    console.warn('[Wizard] Failed to save state:', e);
                }
            }, 1000);
            return () => clearTimeout(timeoutId);
        }
        return undefined;
    }, [isOpen, project?.id, currentStep, completedSteps, protectionMode, projectPath]);

    useEffect(() => {
        const isConfigured = configData.entry_file && ((configData.files || []).length > 0 || configData.settings?.file_tree);
        setShowQuickBuild(!!isConfigured && !isBuilding && currentStep < 5);
    }, [configData.entry_file, configData.files, configData.settings?.file_tree, isBuilding, currentStep]);

    const hasInitializedRef = useRef(false);
    const isUpdatingConfigRef = useRef(false);

    useLayoutEffect(() => {
        if (configData && isOpen && !hasInitializedRef.current) {
            hasInitializedRef.current = true;

            if (configData.skip_obfuscation !== undefined) {
                setEnableObfuscation(!configData.skip_obfuscation);
            }
            if (configData.enable_lease !== undefined) {
                setEnableLease(configData.enable_lease);
            }
            if (configData.fast_build !== undefined) {
                setFastBuild(configData.fast_build);
            }
            if (configData.enable_binary_hash !== undefined) {
                setEnableBinaryHash(configData.enable_binary_hash);
            }
            if (configData.compiler_options?.target) {
                setNodeTarget(configData.compiler_options.target);
            }
        }
    }, [configData, isOpen]);

    useEffect(() => {
        if (!isOpen) {
            hasInitializedRef.current = false;
            setIsDirty(false);
        }
    }, [isOpen]);

    useEffect(() => {
        if (!hasInitializedRef.current || isUpdatingConfigRef.current) {
            return;
        }

        const needsUpdate =
            configData.include_modules?.join(',') !== includePackages.join(',') ||
            configData.exclude_modules?.join(',') !== excludePackages.join(',') ||
            configData.skip_obfuscation !== !enableObfuscation ||
            configData.enable_lease !== enableLease ||
            configData.fast_build !== fastBuild ||
            configData.enable_binary_hash !== enableBinaryHash ||
            configData.nuitka_options?.demo_mode !== demoMode ||
            configData.nuitka_options?.demo_duration !== demoDuration ||
            configData.compiler_options?.target !== nodeTarget;

        if (!needsUpdate) {
            return;
        }

        setIsDirty(true);
        isUpdatingConfigRef.current = true;

        setConfigData((prev: any) => ({
            ...prev,
            include_modules: includePackages,
            exclude_modules: excludePackages,
            skip_obfuscation: !enableObfuscation,
            enable_lease: enableLease,
            fast_build: fastBuild,
            enable_binary_hash: enableBinaryHash,
            nuitka_options: {
                ...prev.nuitka_options,
                demo_mode: demoMode,
                demo_duration: demoDuration
            },
            compiler_options: {
                ...prev.compiler_options,
                target: nodeTarget
            }
        }));

        Promise.resolve().then(() => {
            isUpdatingConfigRef.current = false;
        });
    }, [includePackages, excludePackages, demoMode, demoDuration, nodeTarget, enableObfuscation, enableLease, fastBuild, setConfigData, configData]);

    useEffect(() => {
        if (configData.settings?.file_tree && currentStep === 1) {
            setCompletedSteps(prev => [...new Set([...prev, 1])]);
            setCurrentStep(2);
        }
    }, [configData.settings?.file_tree, currentStep]);

    useEffect(() => {
        if (!projectPath || !isTauri) return;

        const scanProject = async () => {
            try {
                const { invoke } = await import('@tauri-apps/api/core');
                const envResult = await invoke('read_env_file_values', { projectPath }) as Record<string, string>;
                setEnvValues(envResult || {});

                const structure = await invoke('scan_project_structure', { projectPath }) as { data_dirs?: string[] };
                if (structure.data_dirs) {
                    setDetectedDataFolders(structure.data_dirs);
                }
            } catch (error) {
                console.error('Failed to scan project:', error);
                setEnvValues({});
                setDetectedDataFolders([]);
            }
        };

        scanProject();
    }, [projectPath]);

    const canProceed = () => {
        switch (currentStep) {
            case 1:
                return (configData.files || []).length > 0 || !!configData.settings?.file_tree;
            case 2:
                return true;
            case 3:
                return !!configData.entry_file;
            case 4:
                return true;
            case 5:
                return !!configData.entry_file;
            default:
                return false;
        }
    };

    const handleNext = useCallback(async () => {
        if (currentStep < 5 && canProceed()) {
            setCompletedSteps(prev => [...new Set([...prev, currentStep])]);
            setCurrentStep(currentStep + 1);
        }
    }, [currentStep, canProceed]);

    const handleBack = useCallback(() => {
        if (currentStep > 1) {
            const prevStep = currentStep - 1;
            setCurrentStep(prevStep);
            setCompletedSteps(prev => prev.filter(step => step < prevStep));
        }
    }, [currentStep]);

    const handleBrowseProjectPath = useCallback(async () => {
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
    }, [project?.language]);

    const doStartBuild = useCallback(async () => {
        setShowPrereqs(false);
        projectBuild.start('local-installer');
        projectBuild.updateBuild({ progress: 0 });

        try {
            projectBuild.addLog('✅ Starting build...');

            if (isTauri) {
                const { invoke } = await import('@tauri-apps/api/core');

                if (!projectPath) {
                    projectBuild.addLog('⚠️ Please select a project folder first');
                    projectBuild.fail('No project folder selected');
                    return;
                }

                let entryFileName = configData.entry_file || '';

                if (entryFileName && projectPath) {
                    const normalizedEntry = entryFileName.replace(/\\/g, '/');
                    const normalizedProjectPath = projectPath.replace(/\\/g, '/');
                    const pathParts = normalizedProjectPath.split('/');

                    for (let i = pathParts.length - 1; i >= 0; i--) {
                        const suffix = pathParts.slice(i).join('/');
                        if (normalizedEntry.startsWith(suffix + '/')) {
                            entryFileName = normalizedEntry.slice(suffix.length + 1);
                            break;
                        }
                    }
                }

                if (!entryFileName) {
                    projectBuild.addLog('⚠️ No entry file selected');
                    projectBuild.fail('No entry file selected');
                    return;
                }

                projectBuild.addLog(`📁 Project: ${projectPath}`);
                projectBuild.addLog(`📄 Entry: ${entryFileName}`);

                try {
                    const fileExists = await invoke('check_file_exists', {
                        projectPath: projectPath,
                        entryFile: entryFileName
                    });

                    if (!fileExists) {
                        projectBuild.addLog(`❌ Entry file NOT found: ${entryFileName}`);
                        projectBuild.fail('Entry file not found');
                        return;
                    }
                    projectBuild.addLog('✅ Entry file found');
                } catch (fsError) {
                    projectBuild.addLog('⚠️ Could not verify file, attempting build anyway...');
                }

                const language = project?.language === 'nodejs' ? 'nodejs' : 'python';
                const compilerName = language === 'nodejs' ? 'Node.js (pkg → NSIS)' : 'Python (Nuitka → NSIS)';
                const outputBaseName = entryFileName.split(/[/\\]/).pop()?.replace(/\.(py|js|ts|mjs|cjs)$/, '') || 'output';

                projectBuild.addLog('🔧 Build System: Professional Installer');
                projectBuild.addLog(`📦 Distribution: ${distributionType === 'installer' ? 'Windows Installer' : 'Portable Executable'}`);
                projectBuild.addLog(`📋 Compiler: ${compilerName}`);
                projectBuild.updateBuild({ progress: 10 });

                await invoke('run_installer_build', {
                    request: {
                        project_path: projectPath,
                        entry_file: entryFileName,
                        project_name: project?.name || outputBaseName,
                        project_version: "1.0.0",
                        publisher: publisher,
                        language: language,
                        license_key: null,
                        server_url: import.meta.env.VITE_API_URL || 'http://localhost:8000',
                        license_mode: protectionMode === 'demo' ? 'demo' : 'generic',
                        distribution_type: distributionType,
                        create_desktop_shortcut: createDesktopShortcut,
                        create_start_menu: createStartMenu,
                        output_dir: null,
                    }
                });

            } else {
                projectBuild.addLog('⚠️ Compilation only available in desktop app.');
                projectBuild.complete('N/A - Web Mode');
            }
        } catch (error: any) {
            projectBuild.addLog(`❌ Error: ${error.message || error}`);
            projectBuild.fail(error.message || String(error));
        }
    }, [projectPath, configData.entry_file, project?.name, project?.language, protectionMode, distributionType, createDesktopShortcut, createStartMenu, publisher, projectBuild]);

    const handleCheckPrerequisites = useCallback(() => {
        if (isTauri) {
            setShowPrereqs(true);
        } else {
            doStartBuild();
        }
    }, [doStartBuild]);

    const handleClose = useCallback(async () => {
        if (isDirty && currentStep >= 3 && configData.entry_file) {
            try {
                await onConfigSave();
                setIsDirty(false);
            } catch (error) {
                console.error('Failed to save configuration');
            }
        }
        onClose();
    }, [isDirty, currentStep, configData.entry_file, onConfigSave, onClose]);

    const handleViewLicenses = useCallback(async () => {
        await handleClose();
        navigate('/licenses');
    }, [handleClose, navigate]);

    const handleOpenOutputFolder = useCallback(async () => {
        if (!outputPath || !isTauri) return;

        try {
            const { invoke } = await import('@tauri-apps/api/core');
            const lastSep = Math.max(outputPath.lastIndexOf('/'), outputPath.lastIndexOf(''));
            const folderPath = lastSep > 0 ? outputPath.substring(0, lastSep) : outputPath;
            await invoke('open_output_folder', { path: folderPath });
        } catch (error) {
            console.error('Failed to open folder:', error);
        }
    }, [outputPath]);

    const handleStopBuild = useCallback(async () => {
        if (!currentJobId) {
            projectBuild.cancel();
            return;
        }

        try {
            await api.delete(`/build/installer/${currentJobId}/cancel`);
            projectBuild.cancel();
        } catch (error) {
            projectBuild.cancel();
        }
    }, [currentJobId, projectBuild]);

    const handleSetEntryFile = useCallback((value: string) => {
        setConfigData({ ...configData, entry_file: value });
    }, [configData, setConfigData]);

    const renderStep = () => {
        switch (currentStep) {
            case 1:
                return (
                    <Step1Upload
                        onFileUpload={onFileUpload}
                        onZipUpload={onZipUpload}
                        uploadProgress={uploadProgress}
                        uploadPercent={uploadPercent}
                        uploadStage={uploadStage}
                        files={configData.files || []}
                        fileTree={configData.settings?.file_tree}
                        onDeleteFile={onDeleteFile}
                        project={project}
                    />
                );
            case 2:
                return (
                    <Step2Review
                        fileTree={configData.settings?.file_tree}
                        files={configData.files || []}
                        entryPoint={configData.entry_file || configData.settings?.file_tree?.entry_point}
                        entryPointConfidence={configData.settings?.file_tree?.entry_point_confidence}
                    />
                );
            case 3:
                return (
                    <Step3Configure
                        project={project}
                        fileTree={configData.settings?.file_tree}
                        files={configData.files || []}
                        entryFile={configData.entry_file}
                        setEntryFile={handleSetEntryFile}
                        entryPointCandidates={configData.settings?.file_tree?.entry_point_candidates || []}
                        showConsole={showConsole}
                        setShowConsole={setShowConsole}
                        projectPath={projectPath}
                        envValues={envValues}
                        selectedEnvKeys={selectedEnvKeys}
                        setSelectedEnvKeys={setSelectedEnvKeys}
                        iconPath={iconPath}
                        setIconPath={setIconPath}
                        includePackages={includePackages}
                        setIncludePackages={setIncludePackages}
                        excludePackages={excludePackages}
                        setExcludePackages={setExcludePackages}
                        detectedDataFolders={detectedDataFolders}
                        selectedDataFolders={selectedDataFolders}
                        setSelectedDataFolders={setSelectedDataFolders}
                        nodeTarget={nodeTarget}
                        setNodeTarget={setNodeTarget}
                        enableObfuscation={enableObfuscation}
                        setEnableObfuscation={setEnableObfuscation}
                        enableLease={enableLease}
                        setEnableLease={setEnableLease}
                        fastBuild={fastBuild}
                        setFastBuild={setFastBuild}
                        enableBinaryHash={enableBinaryHash}
                        setEnableBinaryHash={setEnableBinaryHash}
                    />
                );
            case 4:
                return (
                    <Step4License
                        protectionMode={protectionMode}
                        setProtectionMode={setProtectionMode}
                        demoMode={demoMode}
                        setDemoMode={setDemoMode}
                        demoDuration={demoDuration}
                        setDemoDuration={setDemoDuration}
                        isPro={configData.is_pro || false}
                        canRemoveBranding={configData.can_remove_branding || false}
                    />
                );
            case 5:
                return (
                    <Step5Build
                        project={project}
                        entryFile={configData.entry_file}
                        showConsole={showConsole}
                        protectionMode={protectionMode}
                        demoDuration={demoDuration}
                        fileTree={configData.settings?.file_tree}
                        isBuilding={isBuilding}
                        buildProgress={buildProgress}
                        buildStatus={buildStatus}
                        buildLogs={buildLogs}
                        outputPath={outputPath}
                        projectPath={projectPath}
                        onBrowseProjectPath={handleBrowseProjectPath}
                        onStartBuild={handleCheckPrerequisites}
                        onStopBuild={handleStopBuild}
                        onOpenOutputFolder={handleOpenOutputFolder}
                        onViewLicenses={handleViewLicenses}
                        distributionType={distributionType}
                        setDistributionType={setDistributionType}
                        createDesktopShortcut={createDesktopShortcut}
                        setCreateDesktopShortcut={setCreateDesktopShortcut}
                        createStartMenu={createStartMenu}
                        setCreateStartMenu={setCreateStartMenu}
                        publisher={publisher}
                        setPublisher={setPublisher}
                        licenseId={configData.selected_license_id}
                        isPro={configData.is_pro || configData.tier === 'business'}
                    />
                );
            default:
                return null;
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {createPortal(
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 animate-fade-in">
                    <div className="w-full h-full flex flex-row overflow-hidden">
                        <aside className="w-72 bg-gray-950 border-r border-white/10 shrink-0 hidden md:block z-10">
                            <WizardSidebar 
                                currentStep={currentStep}
                                completedSteps={completedSteps}
                            />
                        </aside>

                        <main className="flex-1 flex flex-col relative z-0 bg-gray-900/50">
                            <div className="absolute inset-0 pointer-events-none opacity-10"
                                style={{
                                    backgroundImage: 'radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.1) 0%, transparent 50%)'
                                }}
                            />

                            <header className="h-16 px-6 border-b border-white/10 flex items-center justify-between bg-gray-950/95 shrink-0 z-10">
                                <div className="flex items-center gap-3">
                                    <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                                        <span className="text-indigo-400">/</span>
                                        {project?.name || 'Untitled Project'}
                                    </h2>
                                    {configData.tier === 'business' && (
                                        <span className="px-2 py-0.5 text-xs font-bold bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-full uppercase tracking-wider">
                                            Business
                                        </span>
                                    )}
                                    {configData.tier === 'pro' && (
                                        <span className="px-2 py-0.5 text-xs font-bold bg-purple-500 text-white rounded-full uppercase tracking-wider">
                                            Pro
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={handleClose}
                                        aria-label="Close Wizard"
                                        className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-all group"
                                        title="Close Wizard"
                                    >
                                        <X size={20} className="group-hover:rotate-90 transition-transform" />
                                    </button>
                                </div>
                            </header>

                            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 lg:p-10">
                                <div className="max-w-4xl mx-auto">
                                    {configLoading ? (
                                        <div className="flex flex-col items-center justify-center py-20">
                                            <div className="rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500 animate-spin" />
                                            <p className="mt-4 text-slate-400">Loading configuration...</p>
                                        </div>
                                    ) : (
                                        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                                            {showQuickBuild && (
                                                <div className="mb-6 bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 rounded-xl p-4 flex items-center justify-between animate-in fade-in">
                                                    <div>
                                                        <h3 className="font-bold text-white">Ready to Build</h3>
                                                        <p className="text-sm text-slate-400">Your project is configured. Skip ahead?</p>
                                                    </div>
                                                    <button 
                                                        onClick={() => { 
                                                            setCompletedSteps([1, 2, 3, 4]); 
                                                            setCurrentStep(5); 
                                                        }}
                                                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-all"
                                                    >
                                                        ⚡ Jump to Build
                                                    </button>
                                                </div>
                                            )}
                                            <WizardErrorBoundary>
                                                {renderStep()}
                                            </WizardErrorBoundary>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <footer className="h-20 px-6 border-t border-white/10 bg-gray-950 flex items-center justify-between shrink-0 z-10">
                                <button
                                    onClick={handleBack}
                                    disabled={currentStep === 1}
                                    className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-all ${currentStep === 1
                                        ? 'text-slate-600 cursor-not-allowed'
                                        : 'text-slate-400 hover:text-white hover:bg-white/10'
                                        }`}
                                >
                                    <ChevronLeft size={18} />
                                    Back
                                </button>

                                <div className="flex items-center gap-4">
                                    <span className="md:hidden text-sm text-slate-500">
                                        Step {currentStep} / 5
                                    </span>

                                    {currentStep < 5 ? (
                                        <button
                                            onClick={handleNext}
                                            disabled={!canProceed()}
                                            aria-disabled={!canProceed()}
                                            className={`flex items-center gap-2 px-8 py-3 rounded-xl font-bold text-sm uppercase tracking-wide transition-all shadow-lg ${canProceed()
                                                ? 'bg-indigo-600 text-white hover:bg-indigo-500 hover:shadow-indigo-500/25 hover:-translate-y-0.5'
                                                : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                                                }`}
                                        >
                                            Next Step
                                            <ChevronRight size={18} />
                                        </button>
                                    ) : (
                                        <button
                                            onClick={handleClose}
                                            className="flex items-center gap-2 px-8 py-3 rounded-xl font-bold text-sm uppercase tracking-wide bg-emerald-600 text-white hover:bg-emerald-500 shadow-lg hover:shadow-emerald-500/25 hover:-translate-y-0.5 transition-all"
                                        >
                                            Finish Setup
                                        </button>
                                    )}
                                </div>
                            </footer>
                        </main>
                    </div>
                </div>,
                document.body
            )}
            {showPrereqs && createPortal(
                <PrerequisitesCheck
                    isOpen={showPrereqs}
                    onReady={doStartBuild}
                    onDismiss={() => setShowPrereqs(false)}
                    language={project?.language}
                />,
                document.body
            )}
        </>
    );
};

const MemoizedProjectWizard = memo(ProjectWizard);
export default MemoizedProjectWizard;

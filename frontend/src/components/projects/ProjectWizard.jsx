import React, { useState, useRef, useEffect, useMemo, useCallback, memo, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { X, ChevronLeft, ChevronRight, Maximize2, Minimize2 } from 'lucide-react';
import WizardSidebar from './WizardSidebar';
import { Step1Upload, Step2Review, Step3Configure, Step4License, Step5Build } from './WizardSteps';
import PrerequisitesCheck from '../PrerequisitesCheck';
import { useSettings } from '../../contexts/SettingsContext';
import { useProjectBuild } from '../../contexts/BuildContext';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

/**
 * ProjectWizard - Multi-step wizard for configuring and building projects
 * REDESIGN: "Mission Control" Full Screen Layout
 */
import WizardErrorBoundary from './WizardErrorBoundary';

const ProjectWizard = ({
    isOpen,
    onClose,
    project,
    configLoading,
    configData,
    setConfigData,
    uploadProgress,
    onFileUpload,
    onZipUpload,
    onDeleteFile,
    onConfigSave,
    licenses = []
}) => {
    // Get settings from context
    const { settings } = useSettings();

    // Navigation hook
    const navigate = useNavigate();

    // Get persistent build state from context
    const projectBuild = useProjectBuild(project?.id);
    const {
        status: buildStatus,
        progress: buildProgress,
        logs: buildLogs,
        outputPath,
        isBuilding,
        jobId: currentJobId
    } = projectBuild;

    const [currentStep, setCurrentStep] = useState(1);
    const [completedSteps, setCompletedSteps] = useState([]);
    const [isDirty, setIsDirty] = useState(false); // Track if config has unsaved changes
    const [showQuickBuild, setShowQuickBuild] = useState(false); // Show quick build banner
    const [protectionMode, setProtectionMode] = useState('generic'); // 'generic' | 'demo' | 'none'
    const [showConsole, setShowConsole] = useState(true); // Will be set from settings in useEffect
    const [projectPath, setProjectPath] = useState('');
    const [showPrereqs, setShowPrereqs] = useState(false); // Prerequisites modal

    // Advanced Options State - initialized from settings
    const [envValues, setEnvValues] = useState({});           // All detected env vars
    const [selectedEnvKeys, setSelectedEnvKeys] = useState([]); // Which keys to bake
    const [iconPath, setIconPath] = useState(null);           // Custom icon path
    const [includePackages, setIncludePackages] = useState([]);
    const [excludePackages, setExcludePackages] = useState(settings.defaultExcludePackages || []);
    const [detectedDataFolders, setDetectedDataFolders] = useState([]);
    const [selectedDataFolders, setSelectedDataFolders] = useState([]);
    const [demoMode, setDemoMode] = useState(settings.defaultDemoEnabled || false);
    const [demoDuration, setDemoDuration] = useState(settings.defaultDemoDuration || 60); // minutes

    const [nodeTarget, setNodeTarget] = useState('node18-win-x64');
    const [enableObfuscation, setEnableObfuscation] = useState(false); // Obfuscation off by default for faster builds
    const [enableLease, setEnableLease] = useState(false); // Offline lease OFF by default
    const [fastBuild, setFastBuild] = useState(false); // Fast build OFF by default (produces onefile exe)

    // Distribution settings (local state that overrides settings defaults during this wizard session)
    const [distributionType, setDistributionType] = useState(settings.defaultDistributionType || 'portable');
    const [createDesktopShortcut, setCreateDesktopShortcut] = useState(settings.defaultCreateDesktopShortcut ?? true);
    const [createStartMenu, setCreateStartMenu] = useState(settings.defaultCreateStartMenu ?? true);
    const [publisher, setPublisher] = useState(settings.defaultPublisher || '');

    // Reset wizard when opened
    useEffect(() => {
        if (isOpen) {
            const STORAGE_KEY = `codevault_wizard_${project?.id}`;
            const EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

            // PRIORITY 1: If there's an active or recent build, go straight to Step 5
            if (buildStatus === 'running' || buildStatus === 'pending') {
                // Active build - jump to build step immediately
                setCurrentStep(5);
                setCompletedSteps([1, 2, 3, 4]); // Mark all previous steps as complete
            } else if (buildStatus === 'completed' || buildStatus === 'failed') {
                // Recent build result - show the build step so user can see outcome
                setCurrentStep(5);
                setCompletedSteps([1, 2, 3, 4]);
            } else {
                // PRIORITY 2: Check localStorage for saved wizard state
                try {
                    const saved = localStorage.getItem(STORAGE_KEY);
                    if (saved) {
                        const state = JSON.parse(saved);
                        // Check if not expired (24 hours)
                        if (Date.now() - state.timestamp < EXPIRY_MS) {
                            if (import.meta.env.DEV) {
                                console.log('[Wizard] Restoring saved state:', state);
                            }
                            setCurrentStep(state.currentStep || 1);
                            setCompletedSteps(state.completedSteps || []);
                            if (state.protectionMode) setProtectionMode(state.protectionMode);
                            if (state.projectPath) setProjectPath(state.projectPath);
                            return; // Don't run default logic
                        } else {
                            // Expired - clear it
                            localStorage.removeItem(STORAGE_KEY);
                        }
                    }
                } catch (e) {
                    if (import.meta.env.DEV) {
                        console.warn('[Wizard] Failed to restore state:', e);
                    }
                }

                // PRIORITY 3: Default - check if files exist
                const hasFiles = configData.files?.length > 0 || configData.file_tree;
                setCurrentStep(hasFiles ? 2 : 1);
                setCompletedSteps(hasFiles ? [1] : []);
            }

            // Init node options if present
            if (configData.compiler_options?.target) {
                setNodeTarget(configData.compiler_options.target);
            }
        }
    }, [isOpen, configData.files, configData.file_tree, buildStatus]);

    // Save wizard state to localStorage when step changes (debounced)
    useEffect(() => {
        if (isOpen && project?.id && currentStep > 1) {
            const STORAGE_KEY = `codevault_wizard_${project.id}`;
            
            // Debounce localStorage writes by 1 second
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
                    if (import.meta.env.DEV) {
                        console.warn('[Wizard] Failed to save state:', e);
                    }
                }
            }, 1000);

            return () => clearTimeout(timeoutId);
        }
    }, [isOpen, project?.id, currentStep, completedSteps, protectionMode, projectPath]);

    // Quick Build Banner - Show when project is configured and ready
    useEffect(() => {
        const isConfigured = configData.entry_file && (configData.files?.length > 0 || configData.file_tree);
        setShowQuickBuild(isConfigured && !isBuilding && currentStep < 5);
    }, [configData, isBuilding, currentStep]);

    // Track if we've initialized from configData to prevent circular updates
    const hasInitializedRef = useRef(false);
    const isUpdatingConfigRef = useRef(false);

    // Initialize local state from loaded configData ONCE when config is first loaded
    // This runs synchronously before the sync effect to prevent loops
    useLayoutEffect(() => {
        if (configData && isOpen && !hasInitializedRef.current) {
            // Only initialize once per wizard session
            hasInitializedRef.current = true;

            // Sync obfuscation state from config (invert skip_obfuscation to get enableObfuscation)
            if (configData.skip_obfuscation !== undefined) {
                setEnableObfuscation(!configData.skip_obfuscation);
            }
            // Sync lease state from config
            if (configData.enable_lease !== undefined) {
                setEnableLease(configData.enable_lease);
            }
            // Sync fast build state from config
            if (configData.fast_build !== undefined) {
                setFastBuild(configData.fast_build);
            }
            // Sync node target from compiler options
            if (configData.compiler_options?.target) {
                setNodeTarget(configData.compiler_options.target);
            }

            if (import.meta.env.DEV) {
                console.log('[WIZARD] Initialized state from configData');
            }
        }
    }, [configData, isOpen]);

    // Reset initialization flag when wizard closes
    useEffect(() => {
        if (!isOpen) {
            hasInitializedRef.current = false;
        }
    }, [isOpen]);

    // Sync local state to configData for saving - but prevent loops
    useEffect(() => {
        // Skip if we're currently processing an update or haven't initialized
        if (!hasInitializedRef.current || isUpdatingConfigRef.current) {
            return;
        }

        // Check if values actually changed before updating
        const needsUpdate =
            configData.include_modules?.join(',') !== includePackages.join(',') ||
            configData.exclude_modules?.join(',') !== excludePackages.join(',') ||
            configData.skip_obfuscation !== !enableObfuscation ||
            configData.enable_lease !== enableLease ||
            configData.fast_build !== fastBuild ||
            configData.nuitka_options?.demo_mode !== demoMode ||
            configData.nuitka_options?.demo_duration !== demoDuration ||
            configData.compiler_options?.target !== nodeTarget;

        if (!needsUpdate) {
            return;
        }

        if (import.meta.env.DEV) {
            console.log('[WIZARD SYNC] Syncing to configData');
        }

        // Mark as dirty when config changes
        setIsDirty(true);

        isUpdatingConfigRef.current = true;

        setConfigData(prev => ({
            ...prev,
            include_modules: includePackages,
            exclude_modules: excludePackages,
            // Build options that get saved to project settings
            skip_obfuscation: !enableObfuscation,  // Invert: UI shows "enable", config stores "skip"
            enable_lease: enableLease,
            fast_build: fastBuild,  // Fast build mode (skips --onefile for faster compilation)
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

        // Reset the flag after a microtask to allow the state update to propagate
        Promise.resolve().then(() => {
            isUpdatingConfigRef.current = false;
        });
    }, [includePackages, excludePackages, demoMode, demoDuration, nodeTarget, enableObfuscation, enableLease, fastBuild, setConfigData, configData]);

    // Auto-advance after ZIP upload
    useEffect(() => {
        if (configData.file_tree && currentStep === 1) {
            setCompletedSteps(prev => [...new Set([...prev, 1])]);
            setCurrentStep(2);
        }
    }, [configData.file_tree, currentStep]);

    // Scan project structure when projectPath changes (for env vars, data folders)
    useEffect(() => {
        if (!projectPath || !isTauri) return;

        const scanProject = async () => {
            try {
                const { invoke } = await import('@tauri-apps/api/core');

                // Read env file values
                const envResult = await invoke('read_env_file_values', { projectPath });
                setEnvValues(envResult || {});

                // Scan project structure to detect data folders
                const structure = await invoke('scan_project_structure', { projectPath });
                if (structure.data_dirs) {
                    setDetectedDataFolders(structure.data_dirs);
                }
            } catch (error) {
                if (import.meta.env.DEV) {
                    console.error('Failed to scan project:', error);
                }
                setEnvValues({});
                setDetectedDataFolders([]);
            }
        };

        scanProject();
    }, [projectPath]);

    // Listen to Tauri compilation events - REMOVED (Handled globally in BuildContext now)
    // This allows the build to continue updating even if the wizard is closed.
    /* 
    useEffect(() => {
        if (!isTauri || !isOpen || buildStatus !== 'running') return;
        // ... (Listeners moved to BuildContext.jsx)
    }, [isOpen, buildStatus, projectBuild]);
    */

    const canProceed = () => {
        switch (currentStep) {
            case 1:
                return configData.files?.length > 0 || configData.file_tree;
            case 2:
                return true; // Can always proceed from review
            case 3:
                return !!configData.entry_file;
            case 4:
                return true; // License is optional
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
            // Remove any steps >= the step we're moving back to from completed steps
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

            if (selected) {
                setProjectPath(selected);
            }
        } catch (error) {
            if (import.meta.env.DEV) {
                console.error('Failed to open folder picker:', error);
            }
        }
    }, [project?.language]);

    // Called after prerequisites check passes
    const doStartBuild = useCallback(async () => {
        setShowPrereqs(false);

        // Use context methods to update build state (persists across tab switches)
        projectBuild.start();
        projectBuild.updateBuild({ progress: 0 });

        try {
            projectBuild.addLog('✅ Starting build...');

            if (isTauri) {
                const { invoke } = await import('@tauri-apps/api/core');

                // Check if project path is set
                if (!projectPath) {
                    projectBuild.addLog('⚠️ Please select a project folder first');
                    projectBuild.fail('No project folder selected');
                    return;
                }

                let entryFileName = configData.entry_file || '';

                if (entryFileName && projectPath) {
                    // Normalize paths for comparison
                    const normalizedEntry = entryFileName.replace(/\\/g, '/');
                    const normalizedProjectPath = projectPath.replace(/\\/g, '/');

                    // Extract folder names from the project path
                    const pathParts = normalizedProjectPath.split('/');

                    // Try to find where the entry file path overlaps with the selected folder
                    for (let i = pathParts.length - 1; i >= 0; i--) {
                        const suffix = pathParts.slice(i).join('/');
                        if (normalizedEntry.startsWith(suffix + '/')) {
                            // Found overlap! Extract just the remaining file path
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

                // Check if entry file exists
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
                const outputBaseName = entryFileName.split(/[/\\]/).pop().replace(/\.(py|js|ts|mjs|cjs)$/, '') || 'output';

                projectBuild.addLog('🔧 Build System: Professional Installer');
                projectBuild.addLog(`📦 Distribution: ${distributionType === 'installer' ? 'Windows Installer' : 'Portable Executable'}`);
                projectBuild.addLog(`📋 Compiler: ${compilerName}`);
                projectBuild.updateBuild({ progress: 10 });

                // Call the new installer build command
                await invoke('run_installer_build', {
                    request: {
                        project_path: projectPath,
                        entry_file: entryFileName,  // Relative path from project root (e.g., "src/main.js")
                        project_name: project?.name || outputBaseName,
                        project_version: "1.0.0",  // TODO: Get from project settings
                        publisher: publisher,
                        language: language,
                        license_key: null,  // Generic build - no embedded key
                        server_url: import.meta.env.VITE_API_URL || 'http://localhost:8000',
                        license_mode: protectionMode === 'none' ? null : protectionMode === 'demo' ? 'demo' : 'generic',
                        distribution_type: distributionType,
                        create_desktop_shortcut: createDesktopShortcut,
                        create_start_menu: createStartMenu,
                        output_dir: null, // Auto-save next to project folder
                    }
                });

            } else {
                // Web mode - just save config, can't compile
                projectBuild.addLog('⚠️ Compilation only available in desktop app.');
                projectBuild.complete('N/A - Web Mode');
            }
        } catch (error) {
            projectBuild.addLog(`❌ Error: ${error.message || error}`);
            projectBuild.fail(error.message || String(error));
        }
    }, [projectPath, configData.entry_file, project?.name, project?.language, protectionMode, distributionType, createDesktopShortcut, createStartMenu, publisher, projectBuild, onConfigSave]);

    // Show prerequisites check before starting build
    const handleCheckPrerequisites = useCallback(() => {
        if (isTauri) {
            setShowPrereqs(true);
        } else {
            // Web mode - skip prerequisites check
            doStartBuild();
        }
    }, [doStartBuild]);

    // Auto-save config before closing wizard
    const handleClose = useCallback(async () => {
        // Save config only if dirty and we're on or past Step 3 (where settings are configured)
        if (isDirty && currentStep >= 3 && configData.entry_file) {
            try {
                await onConfigSave();
                setIsDirty(false); // Clear dirty flag after successful save
            } catch (error) {
                if (window.showToast) {
                    window.showToast('Failed to save configuration', 'error');
                }
            }
        }
        onClose();
    }, [isDirty, currentStep, configData.entry_file, onConfigSave, onClose]);

    const handleViewLicenses = useCallback(async () => {
        await handleClose(); // Close with auto-save
        navigate('/licenses'); // Navigate to licenses page
    }, [handleClose, navigate]);

    const handleOpenOutputFolder = useCallback(async () => {
        if (!outputPath || !isTauri) return;

        try {
            const { invoke } = await import('@tauri-apps/api/core');
            const lastSep = Math.max(outputPath.lastIndexOf('/'), outputPath.lastIndexOf('\\'));
            const folderPath = lastSep > 0 ? outputPath.substring(0, lastSep) : outputPath;
            await invoke('open_output_folder', { path: folderPath });
        } catch (error) {
            if (import.meta.env.DEV) {
                console.error('Failed to open folder:', error);
            }
        }
    }, [outputPath]);

    // Handle stop/cancel build
    const handleStopBuild = useCallback(async () => {
        if (!currentJobId) {
            projectBuild.cancel();
            return;
        }

        try {
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/build/installer/${currentJobId}/cancel`, {
                method: 'DELETE'
            });

            if (response.ok) {
                projectBuild.cancel();
            }
        } catch (error) {
            projectBuild.cancel();
        }
    }, [currentJobId, projectBuild]);

    const handleSetEntryFile = useCallback((value) => {
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
                        files={configData.files || []}
                        fileTree={configData.file_tree}
                        onDeleteFile={onDeleteFile}
                        project={project}
                    />
                );
            case 2:
                return (
                    <Step2Review
                        fileTree={configData.file_tree}
                        files={configData.files || []}
                        entryPoint={configData.entry_file || configData.file_tree?.entry_point}
                        entryPointConfidence={configData.file_tree?.entry_point_confidence}
                    />
                );
            case 3:
                return (
                    <Step3Configure
                        project={project}
                        fileTree={configData.file_tree}
                        files={configData.files || []}
                        entryFile={configData.entry_file}
                        setEntryFile={handleSetEntryFile}
                        entryPointCandidates={configData.file_tree?.entry_point_candidates || []}
                        showConsole={showConsole}
                        setShowConsole={setShowConsole}
                        // Advanced Options props
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
                        // Node.js props
                        nodeTarget={nodeTarget}
                        setNodeTarget={setNodeTarget}
                        // Obfuscation props
                        enableObfuscation={enableObfuscation}
                        setEnableObfuscation={setEnableObfuscation}
                        // Lease props
                        enableLease={enableLease}
                        setEnableLease={setEnableLease}
                        // Fast build props
                        fastBuild={fastBuild}
                        setFastBuild={setFastBuild}
                    />
                );
            case 4:
                return (
                    <Step4License
                        protectionMode={protectionMode}
                        setProtectionMode={setProtectionMode}
                        // Demo mode props
                        demoMode={demoMode}
                        setDemoMode={setDemoMode}
                        demoDuration={demoDuration}
                        setDemoDuration={setDemoDuration}
                        // Tier info for branding notice (from project config API)
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
                        fileTree={configData.file_tree}
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
                        // Distribution settings
                        distributionType={distributionType}
                        setDistributionType={setDistributionType}
                        createDesktopShortcut={createDesktopShortcut}
                        setCreateDesktopShortcut={setCreateDesktopShortcut}
                        createStartMenu={createStartMenu}
                        setCreateStartMenu={setCreateStartMenu}
                        publisher={publisher}
                        setPublisher={setPublisher}
                        licenseId={configData.selected_license_id}
                        // Cross-platform compilation (Pro tier info)
                        isPro={configData.is_pro || false}
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
                    {/* Full Screen Workspace "Mission Control" */}
                    <div className="w-full h-full flex flex-row overflow-hidden">
                        
                        {/* Sidebar */}
                        <aside className="w-72 bg-gray-950 border-r border-white/10 shrink-0 hidden md:block z-10">
                            <WizardSidebar 
                                currentStep={currentStep}
                                completedSteps={completedSteps}
                            />
                        </aside>

                        {/* Main Content Area */}
                        <main className="flex-1 flex flex-col relative z-0 bg-gray-900/50">
                            {/* Background Texture/Effect - reduced opacity for performance */}
                            <div className="absolute inset-0 pointer-events-none opacity-10"
                                style={{
                                    backgroundImage: 'radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.1) 0%, transparent 50%)'
                                }}
                            />

                            {/* Header */}
                            <header className="h-16 px-6 border-b border-white/10 flex items-center justify-between bg-gray-950/95 shrink-0 z-10">
                                <div className="flex items-center gap-3">
                                    <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                                        <span className="text-indigo-400">/</span>
                                        {project?.name || 'Untitled Project'}
                                    </h2>
                                    {configData.tier === 'enterprise' && (
                                        <span className="px-2 py-0.5 text-xs font-bold bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-full uppercase tracking-wider">
                                            Enterprise
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

                            {/* Scrollable Content */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 lg:p-10">
                                <div className="max-w-4xl mx-auto">
                                    {configLoading ? (
                                        <div className="flex flex-col items-center justify-center py-20">
                                            <div className="rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500 animate-spin" />
                                            <p className="mt-4 text-slate-400">Loading configuration...</p>
                                        </div>
                                    ) : (
                                        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                                            {/* Quick Build Banner */}
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

                            {/* Footer / Action Bar */}
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
                                    {/* Step Counter (Mobile Only) */}
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

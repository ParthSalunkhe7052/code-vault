import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import WizardStepIndicator from './WizardStepIndicator';
import { Step1Upload, Step2Review, Step3Configure, Step4License, Step5Build } from './WizardSteps';
import PrerequisitesCheck from '../PrerequisitesCheck';
import { useSettings } from '../../contexts/SettingsContext';

// Check if we're in Tauri
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

/**
 * ProjectWizard - Multi-step wizard for configuring and building projects
 * Replaces the old ConfigureProjectModal with a guided flow
 */
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

    const [currentStep, setCurrentStep] = useState(1);
    const [completedSteps, setCompletedSteps] = useState([]);
    const [protectionMode, setProtectionMode] = useState('generic'); // 'generic' | 'demo' | 'none'
    const [showConsole, setShowConsole] = useState(true); // Will be set from settings in useEffect
    const [isBuilding, setIsBuilding] = useState(false);
    const [buildStatus, setBuildStatus] = useState('idle');
    const [buildProgress, setBuildProgress] = useState(0);
    const [buildLogs, setBuildLogs] = useState([]);
    const [outputPath, setOutputPath] = useState(null);
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

    // Node.js Options
    const [nodeTarget, setNodeTarget] = useState('node18-win-x64');
    const [enableObfuscation, setEnableObfuscation] = useState(false); // Obfuscation off by default for faster builds

    // Distribution settings (local state that overrides settings defaults during this wizard session)
    const [distributionType, setDistributionType] = useState(settings.defaultDistributionType || 'portable');
    const [createDesktopShortcut, setCreateDesktopShortcut] = useState(settings.defaultCreateDesktopShortcut ?? true);
    const [createStartMenu, setCreateStartMenu] = useState(settings.defaultCreateStartMenu ?? true);
    const [publisher, setPublisher] = useState(settings.defaultPublisher || '');

    // Reset wizard when opened
    useEffect(() => {
        if (isOpen) {
            // If files already exist, start at step 2
            const hasFiles = configData.files?.length > 0 || configData.file_tree;
            setCurrentStep(hasFiles ? 2 : 1);
            setCompletedSteps(hasFiles ? [1] : []);
            setBuildStatus('idle');
            setBuildProgress(0);
            setBuildLogs([]);
            setOutputPath(null);

            // Init node options if present
            if (configData.compiler_options?.target) {
                setNodeTarget(configData.compiler_options.target);
            }
        }
    }, [isOpen, configData.files, configData.file_tree]);

    // Sync local state to configData for saving
    useEffect(() => {
        setConfigData(prev => ({
            ...prev,
            include_modules: includePackages,
            exclude_modules: excludePackages,
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
    }, [includePackages, excludePackages, demoMode, demoDuration, nodeTarget, setConfigData]);

    // Auto-advance after ZIP upload
    useEffect(() => {
        if (configData.file_tree && currentStep === 1) {
            setCompletedSteps(prev => [...new Set([...prev, 1])]);
            setCurrentStep(2);
        }
    }, [configData.file_tree]);

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
                console.error('Failed to scan project:', error);
                setEnvValues({});
                setDetectedDataFolders([]);
            }
        };

        scanProject();
    }, [projectPath]);

    // Listen to Tauri compilation events
    useEffect(() => {
        if (!isTauri || !isOpen || buildStatus !== 'running') return;

        let unlistenProgress = null;
        let unlistenResult = null;

        const setupListeners = async () => {
            const { listen } = await import('@tauri-apps/api/event');

            unlistenProgress = await listen('compilation-progress', (event) => {
                const { progress: prog, message, stage } = event.payload;
                setBuildProgress(prog);
                setBuildLogs(prev => [...prev.slice(-99), message]);
            });

            unlistenResult = await listen('compilation-result', (event) => {
                const { success, output_path, error_message } = event.payload;
                if (success) {
                    setBuildStatus('completed');
                    setOutputPath(output_path);
                    setBuildProgress(100);
                    setBuildLogs(prev => [...prev, `✅ Build complete: ${output_path}`]);
                } else {
                    setBuildStatus('failed');
                    setBuildLogs(prev => [...prev, `❌ Build failed: ${error_message}`]);
                }
                setIsBuilding(false);
            });
        };

        setupListeners();

        return () => {
            unlistenProgress?.then?.(fn => fn?.());
            unlistenResult?.then?.(fn => fn?.());
        };
    }, [isOpen, buildStatus]);

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

    const handleNext = () => {
        if (currentStep < 5 && canProceed()) {
            setCompletedSteps(prev => [...new Set([...prev, currentStep])]);
            setCurrentStep(currentStep + 1);
        }
    };

    const handleBack = () => {
        if (currentStep > 1) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleBrowseProjectPath = async () => {
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
            console.error('Failed to open folder picker:', error);
        }
    };

    // Show prerequisites check before starting build
    const handleCheckPrerequisites = () => {
        if (isTauri) {
            setShowPrereqs(true);
        } else {
            // Web mode - skip prerequisites check
            doStartBuild();
        }
    };

    // Called after prerequisites check passes
    const doStartBuild = async () => {
        setShowPrereqs(false);
        setIsBuilding(true);
        setBuildStatus('running');
        setBuildProgress(0);
        setBuildLogs(['Starting build process...']);
        setOutputPath(null);

        try {
            // First save the config
            await onConfigSave();
            setBuildLogs(prev => [...prev, '✅ Configuration saved']);

            if (isTauri) {
                const { invoke } = await import('@tauri-apps/api/core');

                // Check if project path is set
                if (!projectPath) {
                    setBuildLogs(prev => [...prev, '⚠️ Please select a project folder first']);
                    setBuildStatus('failed');
                    setIsBuilding(false);
                    return;
                }


                // Use the entry file path as-is (it's a relative path from project root)
                // This preserves subdirectory paths like "src/main.js"
                let entryFileName = configData.entry_file || '';

                // Smart path alignment: if the user selected a folder that's already
                // part of the entry file path, extract just the remaining portion.
                // E.g., if entry is "test_project/src/main.js" and user selected
                //       "C:\...\test_project\src", we should look for just "main.js"
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
                            console.log(`Path alignment: adjusted entry from "${normalizedEntry}" to "${entryFileName}"`);
                            break;
                        }
                    }
                }

                if (!entryFileName) {
                    setBuildLogs(prev => [...prev, '⚠️ No entry file selected']);
                    setBuildStatus('failed');
                    setIsBuilding(false);
                    return;
                }

                setBuildLogs(prev => [...prev, `📁 Project: ${projectPath}`, `📄 Entry: ${entryFileName}`]);


                // Check if entry file exists in the selected folder before compiling
                setBuildLogs(prev => [...prev, `🔍 Checking if file exists...`]);

                try {
                    const fileExists = await invoke('check_file_exists', {
                        projectPath: projectPath,
                        entryFile: entryFileName
                    });

                    if (!fileExists) {
                        setBuildLogs(prev => [...prev,
                        `❌ Entry file NOT found: ${entryFileName}`,
                            ``,
                        `📌 Make sure you selected the correct folder containing your ${project?.language === 'nodejs' ? 'JavaScript' : 'Python'} files.`,
                        `   Selected: ${projectPath}`,
                        `   Looking for: ${entryFileName}`,
                            ``,
                            `Hint: If you uploaded a ZIP, the extracted files are on the server,`,
                            `      not in your local folder. Select the correct local folder.`
                        ]);
                        setBuildStatus('failed');
                        setIsBuilding(false);
                        return;
                    }
                    setBuildLogs(prev => [...prev, `✅ Entry file found`]);
                } catch (fsError) {
                    // If fs check fails, try anyway (permission issues)
                    console.warn('Could not check file existence:', fsError);
                    setBuildLogs(prev => [...prev, `⚠️ Could not verify file, attempting build anyway...`]);
                }

                // Use the new professional installer build system
                // This calls the build orchestrator API which handles both portable and installer modes
                const language = project?.language === 'nodejs' ? 'nodejs' : 'python';
                const compilerName = language === 'nodejs' ? 'Node.js (pkg → NSIS)' : 'Python (Nuitka → NSIS)';
                const outputBaseName = entryFileName.split(/[/\\]/).pop().replace(/\.(py|js|ts|mjs|cjs)$/, '') || 'output';

                // Get distribution settings from context
                const distributionType = settings.defaultDistributionType || 'portable';
                const createDesktopShortcut = settings.defaultCreateDesktopShortcut ?? true;
                const createStartMenu = settings.defaultCreateStartMenu ?? true;
                const publisher = settings.defaultPublisher || 'Unknown Publisher';

                setBuildLogs(prev => [...prev,
                    `🔧 Build System: Professional Installer`,
                `📦 Distribution: ${distributionType === 'installer' ? 'Windows Installer' : 'Portable Executable'}`,
                `📋 Compiler: ${compilerName}`
                ]);
                setBuildProgress(10);

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
                        server_url: 'http://localhost:8000',
                        license_mode: protectionMode === 'none' ? null : protectionMode === 'demo' ? 'demo' : 'generic',
                        distribution_type: distributionType,
                        create_desktop_shortcut: createDesktopShortcut,
                        create_start_menu: createStartMenu,
                        output_dir: null, // Auto-save next to project folder
                    }
                });


                // Note: Results come through the event listener above

            } else {
                // Web mode - just save config, can't compile
                setBuildLogs(prev => [...prev, '⚠️ Compilation only available in desktop app.', 'Use the CLI tool to build locally.']);
                setBuildProgress(100);
                setBuildStatus('completed');
                setIsBuilding(false);
            }
        } catch (error) {
            console.error('Build error:', error);
            setBuildLogs(prev => [...prev, `❌ Error: ${error.message || error}`]);
            setBuildStatus('failed');
            setIsBuilding(false);
        }
    };

    const handleOpenOutputFolder = async () => {
        if (!outputPath || !isTauri) return;

        try {
            const { invoke } = await import('@tauri-apps/api/core');
            const lastSep = Math.max(outputPath.lastIndexOf('/'), outputPath.lastIndexOf('\\'));
            const folderPath = lastSep > 0 ? outputPath.substring(0, lastSep) : outputPath;
            await invoke('open_output_folder', { path: folderPath });
        } catch (error) {
            console.error('Failed to open folder:', error);
        }
    };

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
                        setEntryFile={(value) => setConfigData({ ...configData, entry_file: value })}
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
                        onOpenOutputFolder={handleOpenOutputFolder}
                        // Distribution settings
                        distributionType={distributionType}
                        setDistributionType={setDistributionType}
                        createDesktopShortcut={createDesktopShortcut}
                        setCreateDesktopShortcut={setCreateDesktopShortcut}
                        createStartMenu={createStartMenu}
                        setCreateStartMenu={setCreateStartMenu}
                        publisher={publisher}
                        setPublisher={setPublisher}
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
                    {/* Click outside to close */}
                    <div className="absolute inset-0" onClick={onClose} />

                    <div className="relative max-w-4xl w-full bg-gray-900/98 border border-white/15 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden transform transition-all animate-scale-in flex flex-col max-h-[90vh]">
                        {/* Header */}
                        <div className="flex items-center justify-between p-5 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent shrink-0">
                            <h3 className="font-bold text-lg text-white">
                                Configure Project: {project?.name || ''}
                            </h3>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-all"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Step Indicator */}
                        <div className="border-b border-white/10 shrink-0">
                            <WizardStepIndicator
                                currentStep={currentStep}
                                completedSteps={completedSteps}
                            />
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                            {configLoading ? (
                                <div className="flex items-center justify-center py-20">
                                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500" />
                                </div>
                            ) : (
                                renderStep()
                            )}
                        </div>

                        {/* Footer Navigation */}
                        <div className="flex items-center justify-between p-5 border-t border-white/10 bg-white/5 shrink-0">
                            <button
                                onClick={handleBack}
                                disabled={currentStep === 1}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${currentStep === 1
                                    ? 'text-slate-600 cursor-not-allowed'
                                    : 'text-slate-400 hover:text-white hover:bg-white/10'
                                    }`}
                            >
                                <ChevronLeft size={18} />
                                Back
                            </button>

                            <div className="flex items-center gap-3">
                                <span className="text-sm text-slate-400">
                                    Step {currentStep} of 5
                                </span>

                                {currentStep < 5 ? (
                                    <button
                                        onClick={handleNext}
                                        disabled={!canProceed()}
                                        className={`flex items-center gap-2 px-5 py-2.5 rounded-lg font-medium transition-all ${canProceed()
                                            ? 'bg-indigo-600 text-white hover:bg-indigo-500'
                                            : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                                            }`}
                                    >
                                        Next
                                        <ChevronRight size={18} />
                                    </button>
                                ) : (
                                    <button
                                        onClick={onClose}
                                        className="px-5 py-2.5 rounded-lg font-medium bg-white/10 text-white hover:bg-white/20 transition-colors"
                                    >
                                        Done
                                    </button>
                                )}
                            </div>
                        </div>
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

export default ProjectWizard;


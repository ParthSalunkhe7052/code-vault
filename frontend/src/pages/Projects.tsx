import React, { useEffect, useState, useRef } from 'react';
import { Plus, Folder } from 'lucide-react';
import { projects as projectApi, compile as compileApi, licenses as licensesApi } from '../services/api';
import { 
    useProjects, 
    useCreateProject, 
    useDeleteProject 
} from '../hooks/useProjects';
import { ProjectCard, CreateProjectModal, ProjectWizard } from '../components/projects';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import EmptyState from '../components/EmptyState';
import Spinner from '../components/Spinner';
import { Project, License } from '../types/api';

const Projects: React.FC = () => {
    const toast = useToast();
    
    // Queries & Mutations
    const { data: projects = [], isLoading: loading } = useProjects();
    const createProjectMutation = useCreateProject();
    const deleteProjectMutation = useDeleteProject();

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
    const [selectedProject, setSelectedProject] = useState<Project | null>(null);
    const [newProject, setNewProject] = useState({ name: '', description: '', language: 'python' as 'python' | 'nodejs' });
    const [configData, setConfigData] = useState<any>({
        entry_file: '',
        output_name: '',
        include_modules: [],
        exclude_modules: [],
        nuitka_options: {},
        files: [],
        settings: {
            file_tree: null
        },
        skip_obfuscation: true,
        enable_lease: false,
        compiler_options: {}
    });
    const [configLoading, setConfigLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(false);
    const [uploadPercent, setUploadPercent] = useState(0);
    const [uploadStage, setUploadStage] = useState('uploading');
    const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
    const [compileStatus, setCompileStatus] = useState<any>(null);
    const [projectLicenses, setProjectLicenses] = useState<License[]>([]);
    const [confirmDialog, setConfirmDialog] = useState<{
        isOpen: boolean;
        title: string;
        message: string;
        onConfirm: () => void;
        confirmVariant: 'danger' | 'warning' | 'primary';
    }>({
        isOpen: false,
        title: '',
        message: '',
        onConfirm: () => { },
        confirmVariant: 'danger'
    });
    const dropdownRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Auto-open wizard from URL query param
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const projectIdFromUrl = params.get('project_id');
        
        if (projectIdFromUrl && projects.length > 0 && !isConfigModalOpen) {
            const targetProject = projects.find(p => p.id === projectIdFromUrl);
            if (targetProject) {
                handleProjectClick(targetProject);
                window.history.replaceState({}, '', '/projects');
            }
        }
    }, [projects, isConfigModalOpen]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setActiveDropdown(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    useEffect(() => {
        let interval: any;
        let isMounted = true;

        if (compileStatus && (compileStatus.status === 'running' || compileStatus.status === 'pending')) {
            interval = setInterval(async () => {
                if (!isMounted) return;
                try {
                    const status = await compileApi.getStatus(compileStatus.id);
                    if (isMounted) {
                        setCompileStatus(status);
                    }
                } catch (error) {
                    if (isMounted) {
                        console.error('Failed to fetch compile status:', error);
                    }
                }
            }, 5000);
        }

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, [compileStatus]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!newProject.name?.trim()) {
            toast.error('Project name is required');
            return;
        }

        try {
            await createProjectMutation.mutateAsync(newProject);
            setIsModalOpen(false);
            setNewProject({ name: '', description: '', language: 'python' });
            toast.success('Project created successfully');
        } catch (error: any) {
            console.error('Failed to create project:', error);
            const errorMessage = error.response?.data?.detail || 'Failed to create project';
            toast.error(errorMessage);
        }
    };

    const handleProjectClick = async (project: Project) => {
        setSelectedProject(project);
        setConfigLoading(true);
        setIsConfigModalOpen(true);
        setCompileStatus(null);
        setProjectLicenses([]);

        try {
            const licenses = await licensesApi.list(project.id);
            setProjectLicenses(licenses || []);
        } catch (err) {
            console.error('Failed to fetch licenses:', err);
        }

        try {
            const config = await projectApi.getConfig(project.id);
            
            // Backend might return settings as a JSON string
            let parsedSettings = config.settings;
            if (typeof parsedSettings === 'string') {
                try {
                    parsedSettings = JSON.parse(parsedSettings);
                } catch (e) {
                    console.warn('Failed to parse settings JSON:', e);
                    parsedSettings = {};
                }
            }
            parsedSettings = parsedSettings || {};

            setConfigData({
                entry_file: config.entry_file || '',
                output_name: config.output_name || '',
                include_modules: config.include_modules || [],
                exclude_modules: config.exclude_modules || [],
                nuitka_options: config.nuitka_options || {},
                files: config.files || [],
                settings: {
                    ...parsedSettings,
                    file_tree: parsedSettings.file_tree || null
                },
                skip_obfuscation: config.skip_obfuscation ?? true,
                enable_lease: config.enable_lease ?? false,
                enable_binary_hash: config.enable_binary_hash ?? false,
                compiler_options: config.compiler_options || {}
            });
        } catch (error) {
            console.error('Failed to fetch project config:', error);
            setConfigData({
                entry_file: '',
                output_name: '',
                include_modules: [],
                exclude_modules: [],
                nuitka_options: {},
                files: [],
                skip_obfuscation: true,
                enable_lease: false,
                compiler_options: {}
            });
        } finally {
            setConfigLoading(false);
        }
    };

    const handleConfigSave = async (showNotification = false) => {
        if (!selectedProject) return;
        try {
            await projectApi.updateConfig(selectedProject.id, {
                entry_file: configData.entry_file,
                output_name: configData.output_name,
                include_modules: configData.include_modules,
                exclude_modules: configData.exclude_modules,
                nuitka_options: configData.nuitka_options,
                compiler_options: configData.compiler_options,
                skip_obfuscation: configData.skip_obfuscation,
                enable_lease: configData.enable_lease,
                enable_binary_hash: configData.enable_binary_hash
            });
            if (showNotification) {
                toast.success('Configuration saved!');
            }
        } catch (error) {
            console.error('Failed to save config:', error);
            toast.error('Failed to save configuration');
        }
    };

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files || files.length === 0 || !selectedProject) return;

        const MAX_FILE_SIZE = 100 * 1024 * 1024;
        const MAX_TOTAL_SIZE = 500 * 1024 * 1024;
        const ALLOWED_EXTENSIONS = ['.py', '.js', '.ts', '.json', '.txt', '.yml', '.yaml', '.md', '.html', '.css', '.jsx', '.tsx', '.mjs', '.cjs'];

        const fileArray = Array.from(files);
        let totalSize = 0;
        for (let i = 0; i < fileArray.length; i++) {
            const file = fileArray[i];
            if (file && file.size > MAX_FILE_SIZE) {
                toast.error(`File "${file.name}" exceeds 100MB limit`);
                return;
            }
            if (file) {
                totalSize += file.size;
            }
        }

        if (totalSize > MAX_TOTAL_SIZE) {
            toast.error('Total upload size exceeds 500MB limit');
            return;
        }

        for (let i = 0; i < fileArray.length; i++) {
            const file = fileArray[i];
            if (file) {
                const ext = '.' + file.name.split('.').pop()?.toLowerCase();
                if (!ALLOWED_EXTENSIONS.includes(ext || '')) {
                    toast.warning(`File type "${ext}" may not be supported`);
                }
            }
        }

        setUploadProgress(true);
        setUploadPercent(0);
        setUploadStage('uploading');
        try {
            const uploaded = await projectApi.uploadFiles(selectedProject.id, fileArray, (percent) => {
                setUploadPercent(percent);
                if (percent === 100) {
                    setUploadStage('processing');
                }
            });
            if (uploaded && Array.isArray(uploaded)) {
                setConfigData((prev: any) => ({
                    ...prev,
                    files: [...uploaded, ...prev.files]
                }));
                toast.success(`${uploaded.length} file(s) uploaded!`);
            }
        } catch (error: any) {
            console.error('Failed to upload files:', error);
            toast.error('Failed to upload files: ' + (error.response?.data?.detail || error.message));
        } finally {
            setUploadProgress(false);
            setUploadPercent(0);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleZipUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !selectedProject) return;

        if (!file.name.endsWith('.zip')) {
            toast.error('Please upload a .zip file');
            return;
        }

        const MAX_ZIP_SIZE = 500 * 1024 * 1024;
        if (file.size > MAX_ZIP_SIZE) {
            toast.error('ZIP file exceeds 500MB limit');
            return;
        }

        setUploadProgress(true);
        setUploadPercent(0);
        setUploadStage('uploading');
        try {
            const result = await projectApi.uploadZip(selectedProject.id, file, (percent) => {
                setUploadPercent(percent);
                if (percent === 100) {
                    setUploadStage('extracting');
                }
            });

            setConfigData((prev: any) => ({
                ...prev,
                settings: {
                    ...prev.settings,
                    file_tree: result.structure
                },
                entry_file: result.structure.entry_point || '',
                files: []
            }));

            toast.success(`✅ Uploaded ${result.file_count} files from ZIP!`);
        } catch (error: any) {
            console.error('Failed to upload ZIP:', error);
            toast.error('Failed to upload ZIP: ' + (error.response?.data?.detail || error.message));
        } finally {
            setUploadProgress(false);
            setUploadPercent(0);
            e.target.value = '';
        }
    };

    const handleDeleteFile = async (fileId: string) => {
        if (!selectedProject) return;
        setConfirmDialog({
            isOpen: true,
            title: 'Delete File',
            message: 'Are you sure you want to delete this file?',
            confirmVariant: 'danger',
            onConfirm: async () => {
                try {
                    await projectApi.deleteFile(selectedProject.id, fileId);
                    setConfigData((prev: any) => ({
                        ...prev,
                        files: prev.files.filter((f: any) => f.id !== fileId)
                    }));
                    toast.success('File deleted successfully');
                } catch (error) {
                    console.error('Failed to delete file:', error);
                    toast.error('Failed to delete file');
                }
            }
        });
    };

    const handleDeleteProject = async (projectId: string) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Delete Project',
            message: 'Are you sure you want to delete this project? This will remove all files and licenses associated with it.',
            confirmVariant: 'danger',
            onConfirm: async () => {
                try {
                    await deleteProjectMutation.mutateAsync(projectId);
                    setActiveDropdown(null);
                    toast.success('Project deleted successfully');
                } catch (error) {
                    console.error('Failed to delete project:', error);
                    toast.error('Failed to delete project');
                }
            }
        });
    };

    const toggleDropdown = (e: React.MouseEvent, projectId: string) => {
        e.stopPropagation();
        setActiveDropdown(activeDropdown === projectId ? null : projectId);
    };

    return (
        <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Projects</h1>
                    <p className="text-slate-400">Manage your software portfolio.</p>
                </div>
                <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
                    <Plus size={20} />
                    New Project
                </button>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20">
                    <Spinner size="lg" />
                </div>
            ) : projects.length === 0 ? (
                <div className="glass-card">
                    <EmptyState
                        icon={Folder}
                        title="No Projects Found"
                        description="Get started by creating your first project to manage licenses and distributions."
                        action={() => setIsModalOpen(true)}
                        actionLabel="Create Project"
                    />
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project, index) => (
                        <ProjectCard
                            key={project.id}
                            project={project}
                            index={index}
                            activeDropdown={activeDropdown}
                            dropdownRef={dropdownRef}
                            onProjectClick={handleProjectClick}
                            onDropdownToggle={toggleDropdown}
                            onDelete={handleDeleteProject}
                        />
                    ))}
                </div>
            )}

            <CreateProjectModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                newProject={newProject}
                setNewProject={setNewProject}
                onSubmit={handleCreate}
                projectCount={projects.length}
            />

            <ProjectWizard
                isOpen={isConfigModalOpen}
                onClose={() => {
                    setIsConfigModalOpen(false);
                    setCompileStatus(null);
                }}
                project={selectedProject}
                configLoading={configLoading}
                configData={configData}
                setConfigData={setConfigData}
                uploadProgress={uploadProgress}
                uploadPercent={uploadPercent}
                uploadStage={uploadStage}
                onFileUpload={handleFileUpload}
                onZipUpload={handleZipUpload}
                onDeleteFile={handleDeleteFile}
                onConfigSave={handleConfigSave}
                licenses={projectLicenses}
            />

            <ConfirmDialog
                isOpen={confirmDialog.isOpen}
                onClose={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
                onConfirm={confirmDialog.onConfirm}
                title={confirmDialog.title}
                message={confirmDialog.message}
                confirmText="Delete"
                confirmVariant={confirmDialog.confirmVariant}
            />
        </div>
    );
};

export default Projects;

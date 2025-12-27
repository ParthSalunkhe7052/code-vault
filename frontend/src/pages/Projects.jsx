import { useEffect, useState, useRef } from 'react';
import { Plus, Folder } from 'lucide-react';
import { projects as projectApi, compile as compileApi, licenses as licensesApi } from '../services/api';
import { ProjectCard, CreateProjectModal, ProjectWizard } from '../components/projects';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';
import EmptyState from '../components/EmptyState';
import Spinner from '../components/Spinner';

const Projects = () => {
    const toast = useToast();
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
    const [selectedProject, setSelectedProject] = useState(null);
    const [newProject, setNewProject] = useState({ name: '', description: '', language: 'python' });
    const [configData, setConfigData] = useState({
        entry_file: '',
        output_name: '',
        include_modules: [],
        exclude_modules: [],
        nuitka_options: {},
        files: []
    });
    const [configLoading, setConfigLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(false);
    const [activeDropdown, setActiveDropdown] = useState(null);
    const [compileStatus, setCompileStatus] = useState(null);
    const [isCompiling, setIsCompiling] = useState(false);
    const [projectLicenses, setProjectLicenses] = useState([]);
    const [confirmDialog, setConfirmDialog] = useState({
        isOpen: false,
        title: '',
        message: '',
        onConfirm: () => { },
        confirmVariant: 'danger'
    });
    const dropdownRef = useRef(null);
    const fileInputRef = useRef(null);

    const fetchProjects = async () => {
        try {
            const data = await projectApi.list();
            setProjects(data);
        } catch (error) {
            console.error('Failed to fetch projects:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setActiveDropdown(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    // Poll compile status
    useEffect(() => {
        let interval;
        if (compileStatus && (compileStatus.status === 'running' || compileStatus.status === 'pending')) {
            interval = setInterval(async () => {
                try {
                    const status = await compileApi.getStatus(compileStatus.id);
                    setCompileStatus(status);
                    if (status.status === 'completed' || status.status === 'failed') {
                        setIsCompiling(false);
                    }
                } catch (error) {
                    console.error('Failed to fetch compile status:', error);
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [compileStatus]);

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            await projectApi.create(newProject);
            setIsModalOpen(false);
            setNewProject({ name: '', description: '', language: 'python' });
            toast.success('Project created successfully');
            fetchProjects();
        } catch (error) {
            console.error('Failed to create project:', error);
            toast.error('Failed to create project');
        }
    };

    const handleProjectClick = async (project) => {
        setSelectedProject(project);
        setConfigLoading(true);
        setIsConfigModalOpen(true);
        setCompileStatus(null);
        setProjectLicenses([]);

        // Fetch licenses for this project
        try {
            const licenses = await licensesApi.list(project.id);
            setProjectLicenses(licenses || []);
        } catch (err) {
            console.error('Failed to fetch licenses:', err);
        }

        try {
            const config = await projectApi.getConfig(project.id);
            setConfigData({
                entry_file: config.entry_file || '',
                output_name: config.output_name || '',
                include_modules: config.include_modules || [],
                exclude_modules: config.exclude_modules || [],
                nuitka_options: config.nuitka_options || {},
                files: config.files || [],
                file_tree: config.settings?.file_tree || null
            });
        } catch (error) {
            console.error('Failed to fetch project config:', error);
            setConfigData({
                entry_file: '',
                output_name: '',
                include_modules: [],
                exclude_modules: [],
                nuitka_options: {},
                files: []
            });
        } finally {
            setConfigLoading(false);
        }
    };

    const handleConfigSave = async () => {
        try {
            await projectApi.updateConfig(selectedProject.id, {
                entry_file: configData.entry_file,
                output_name: configData.output_name,
                include_modules: configData.include_modules,
                exclude_modules: configData.exclude_modules,
                nuitka_options: configData.nuitka_options
            });
            toast.success('Configuration saved!');
        } catch (error) {
            console.error('Failed to save config:', error);
            toast.error('Failed to save configuration');
        }
    };

    const handleFileUpload = async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        setUploadProgress(true);
        try {
            const uploaded = await projectApi.uploadFiles(selectedProject.id, files);
            console.log('Upload response:', uploaded);
            if (uploaded && Array.isArray(uploaded)) {
                setConfigData(prev => ({
                    ...prev,
                    files: [...uploaded, ...prev.files]
                }));
                toast.success(`${uploaded.length} file(s) uploaded!`);
            }
        } catch (error) {
            console.error('Failed to upload files:', error);
            toast.error('Failed to upload files: ' + (error.response?.data?.detail || error.message));
        } finally {
            setUploadProgress(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleZipUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.name.endsWith('.zip')) {
            toast.error('Please upload a .zip file');
            return;
        }

        setUploadProgress(true);
        try {
            const result = await projectApi.uploadZip(selectedProject.id, file);

            setConfigData(prev => ({
                ...prev,
                file_tree: result.structure,
                entry_file: result.structure.entry_point || '', // Auto-set entry file
                files: [] // Clear individual files when ZIP is uploaded
            }));

            toast.success(`✅ Uploaded ${result.file_count} files from ZIP!`);
        } catch (error) {
            console.error('Failed to upload ZIP:', error);
            toast.error('Failed to upload ZIP: ' + (error.response?.data?.detail || error.message));
        } finally {
            setUploadProgress(false);
            e.target.value = ''; // Reset file input
        }
    };

    const handleDeleteFile = async (fileId) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Delete File',
            message: 'Are you sure you want to delete this file?',
            confirmVariant: 'danger',
            onConfirm: async () => {
                try {
                    await projectApi.deleteFile(selectedProject.id, fileId);
                    setConfigData(prev => ({
                        ...prev,
                        files: prev.files.filter(f => f.id !== fileId)
                    }));
                    toast.success('File deleted successfully');
                } catch (error) {
                    console.error('Failed to delete file:', error);
                    toast.error('Failed to delete file');
                }
            }
        });
    };

    const handleStartCompile = async () => {
        // Check if either files or file_tree exists
        if (!configData.files.length && !configData.file_tree) {
            toast.warning('Please upload files or a ZIP before compiling.');
            return;
        }

        setIsCompiling(true);
        try {
            const job = await compileApi.start(selectedProject.id, {
                entry_file: configData.entry_file,
                output_name: configData.output_name || selectedProject.name,
                options: configData.nuitka_options
            });
            setCompileStatus(job);
            toast.info('Compilation started...');
        } catch (error) {
            console.error('Failed to start compilation:', error);
            toast.error('Failed to start compilation');
            setIsCompiling(false);
        }
    };

    const handleDeleteProject = async (projectId) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Delete Project',
            message: 'Are you sure you want to delete this project? This will remove all files and licenses associated with it.',
            confirmVariant: 'danger',
            onConfirm: async () => {
                try {
                    await projectApi.delete(projectId);
                    setActiveDropdown(null);
                    toast.success('Project deleted successfully');
                    fetchProjects();
                } catch (error) {
                    console.error('Failed to delete project:', error);
                    toast.error('Failed to delete project');
                }
            }
        });
    };

    const toggleDropdown = (e, projectId) => {
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
                onFileUpload={handleFileUpload}
                onZipUpload={handleZipUpload}
                onDeleteFile={handleDeleteFile}
                onConfigSave={handleConfigSave}
                licenses={projectLicenses}
            />

            {/* Confirm Dialog */}
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

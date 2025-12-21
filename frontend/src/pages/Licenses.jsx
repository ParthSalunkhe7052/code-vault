import React, { useEffect, useState } from 'react';
import { Plus, Search, Filter, Download, Ban, Trash2, CheckCircle, XCircle, AlertTriangle, Key, Calendar, Monitor, Copy, Folder, ChevronLeft, ChevronRight } from 'lucide-react';
import { licenses as licenseApi, projects as projectApi } from '../services/api';
import { CreateLicenseModal, BindingsModal } from '../components/licenses';
import { useToast } from '../components/Toast';
import ConfirmDialog from '../components/ConfirmDialog';

const Licenses = () => {
    const toast = useToast();
    const [licenses, setLicenses] = useState([]);
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isBindingsModalOpen, setIsBindingsModalOpen] = useState(false);
    const [selectedLicense, setSelectedLicense] = useState(null);
    const [bindings, setBindings] = useState([]);
    const [bindingsLoading, setBindingsLoading] = useState(false);
    const [resetStatus, setResetStatus] = useState(null);
    const [resetting, setResetting] = useState(false);

    // Confirm Dialog State
    const [confirmDialog, setConfirmDialog] = useState({
        isOpen: false,
        title: '',
        message: '',
        onConfirm: () => { },
        confirmText: 'Confirm',
        confirmVariant: 'danger'
    });

    // Search and Filter
    const [searchQuery, setSearchQuery] = useState('');
    const [filterProject, setFilterProject] = useState('');
    const [filterStatus, setFilterStatus] = useState('');

    // Pagination
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage] = useState(10);

    // Bulk Selection
    const [selectedLicenses, setSelectedLicenses] = useState(new Set());

    // Features input
    const [featureInput, setFeatureInput] = useState('');

    const [newLicense, setNewLicense] = useState({
        project_id: '',
        client_name: '',
        client_email: '',
        max_machines: 1,
        expires_at: '',
        notes: '',
        features: []
    });

    const fetchData = async () => {
        try {
            const [licensesData, projectsData] = await Promise.all([
                licenseApi.list(),
                projectApi.list()
            ]);
            setLicenses(licensesData);
            setProjects(projectsData);
            if (projectsData.length > 0 && !newLicense.project_id) {
                setNewLicense(prev => ({ ...prev, project_id: projectsData[0].id }));
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    // Reset page when filters change
    useEffect(() => {
        setCurrentPage(1);
    }, [searchQuery, filterProject, filterStatus]);

    // Filter and search licenses
    const filteredLicenses = licenses.filter(license => {
        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            const matchesSearch =
                license.license_key.toLowerCase().includes(query) ||
                (license.client_name && license.client_name.toLowerCase().includes(query)) ||
                (license.client_email && license.client_email.toLowerCase().includes(query));
            if (!matchesSearch) return false;
        }

        // Project filter
        if (filterProject && license.project_id !== filterProject) {
            return false;
        }

        // Status filter
        if (filterStatus && license.status !== filterStatus) {
            return false;
        }

        return true;
    });

    // Pagination
    const totalPages = Math.ceil(filteredLicenses.length / itemsPerPage);
    const paginatedLicenses = filteredLicenses.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    // Get project name - prioritize from license data, fallback to projects lookup
    const getProjectName = (license) => {
        // Use project_name from API if available
        if (license.project_name) {
            return license.project_name;
        }
        // Fallback to looking up in projects array
        const project = projects.find(p => p.id === license.project_id);
        return project ? project.name : 'Deleted Project';
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            const licenseData = {
                ...newLicense,
                expires_at: newLicense.expires_at ? new Date(newLicense.expires_at).toISOString() : null
            };
            await licenseApi.create(licenseData);
            setIsModalOpen(false);
            setNewLicense({
                project_id: projects[0]?.id || '',
                client_name: '',
                client_email: '',
                max_machines: 1,
                expires_at: '',
                notes: '',
                features: []
            });
            setFeatureInput('');
            fetchData();
        } catch (error) {
            console.error('Failed to create license:', error);
        }
    };

    const handleAddFeature = () => {
        const feature = featureInput.trim();
        if (feature && !newLicense.features.includes(feature)) {
            setNewLicense(prev => ({
                ...prev,
                features: [...prev.features, feature]
            }));
            setFeatureInput('');
        }
    };

    const handleRemoveFeature = (feature) => {
        setNewLicense(prev => ({
            ...prev,
            features: prev.features.filter(f => f !== feature)
        }));
    };

    const handleRevoke = async (id) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Revoke License',
            message: 'Are you sure you want to revoke this license? The client will no longer be able to use it.',
            confirmText: 'Revoke',
            confirmVariant: 'warning',
            onConfirm: async () => {
                try {
                    await licenseApi.revoke(id);
                    toast.success('License revoked successfully');
                    fetchData();
                } catch (error) {
                    console.error('Failed to revoke license:', error);
                    toast.error('Failed to revoke license');
                }
            }
        });
    };

    const handleDelete = async (id) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Delete License',
            message: 'Are you sure you want to delete this license? This action cannot be undone.',
            confirmText: 'Delete',
            confirmVariant: 'danger',
            onConfirm: async () => {
                try {
                    await licenseApi.delete(id);
                    setSelectedLicenses(prev => {
                        const newSet = new Set(prev);
                        newSet.delete(id);
                        return newSet;
                    });
                    toast.success('License deleted successfully');
                    fetchData();
                } catch (error) {
                    console.error('Failed to delete license:', error);
                    toast.error('Failed to delete license');
                }
            }
        });
    };

    // Bulk Operations
    const handleSelectAll = () => {
        if (selectedLicenses.size === paginatedLicenses.length) {
            setSelectedLicenses(new Set());
        } else {
            setSelectedLicenses(new Set(paginatedLicenses.map(l => l.id)));
        }
    };

    const handleSelectLicense = (id) => {
        setSelectedLicenses(prev => {
            const newSet = new Set(prev);
            if (newSet.has(id)) {
                newSet.delete(id);
            } else {
                newSet.add(id);
            }
            return newSet;
        });
    };

    const handleBulkRevoke = async () => {
        setConfirmDialog({
            isOpen: true,
            title: 'Revoke Multiple Licenses',
            message: `Are you sure you want to revoke ${selectedLicenses.size} license(s)?`,
            confirmText: 'Revoke All',
            confirmVariant: 'warning',
            onConfirm: async () => {
                try {
                    await Promise.all([...selectedLicenses].map(id => licenseApi.revoke(id)));
                    toast.success(`${selectedLicenses.size} license(s) revoked successfully`);
                    setSelectedLicenses(new Set());
                    fetchData();
                } catch (error) {
                    console.error('Failed to bulk revoke:', error);
                    toast.error('Failed to revoke some licenses');
                }
            }
        });
    };

    const handleBulkDelete = async () => {
        setConfirmDialog({
            isOpen: true,
            title: 'Delete Multiple Licenses',
            message: `Are you sure you want to DELETE ${selectedLicenses.size} license(s)? This cannot be undone!`,
            confirmText: 'Delete All',
            confirmVariant: 'danger',
            onConfirm: async () => {
                try {
                    await Promise.all([...selectedLicenses].map(id => licenseApi.delete(id)));
                    toast.success(`${selectedLicenses.size} license(s) deleted successfully`);
                    setSelectedLicenses(new Set());
                    fetchData();
                } catch (error) {
                    console.error('Failed to bulk delete:', error);
                    toast.error('Failed to delete some licenses');
                }
            }
        });
    };

    const handleExportCSV = () => {
        const dataToExport = selectedLicenses.size > 0
            ? filteredLicenses.filter(l => selectedLicenses.has(l.id))
            : filteredLicenses;

        const headers = ['License Key', 'Client Name', 'Client Email', 'Status', 'Project', 'Max Machines', 'Active Machines', 'Expires At', 'Created At', 'Features'];
        const rows = dataToExport.map(l => [
            l.license_key,
            l.client_name || '',
            l.client_email || '',
            l.status,
            getProjectName(l),
            l.max_machines,
            l.active_machines,
            l.expires_at ? new Date(l.expires_at).toISOString() : 'Never',
            new Date(l.created_at).toISOString(),
            (l.features || []).join('; ')
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `licenses_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        toast.success('Copied to clipboard');
    };

    const handleViewBindings = async (license) => {
        setSelectedLicense(license);
        setIsBindingsModalOpen(true);
        setBindingsLoading(true);
        try {
            const [bindingsData, resetStatusData] = await Promise.all([
                licenseApi.getBindings(license.id),
                licenseApi.getResetStatus(license.id)
            ]);
            setBindings(bindingsData);
            setResetStatus(resetStatusData);
        } catch (error) {
            console.error('Failed to fetch bindings:', error);
            setBindings([]);
            setResetStatus(null);
        } finally {
            setBindingsLoading(false);
        }
    };

    const handleResetHwid = async () => {
        if (!selectedLicense) return;

        // Check if resets are available
        if (resetStatus && resetStatus.resets_remaining <= 0) {
            toast.warning('No HWID resets remaining this month. Please try again next month.');
            return;
        }

        if (bindings.length === 0) {
            toast.info('No hardware bindings to reset.');
            return;
        }

        setConfirmDialog({
            isOpen: true,
            title: 'Reset HWID Bindings',
            message: 'This will remove all hardware bindings for this license. The client will need to reactivate on their machines.',
            confirmText: 'Reset HWID',
            confirmVariant: 'warning',
            onConfirm: async () => {
                setResetting(true);
                try {
                    const result = await licenseApi.resetHwid(selectedLicense.id);
                    toast.success(`HWID reset successful! ${result.bindings_removed} binding(s) removed.`);
                    setBindings([]);
                    setResetStatus(prev => prev ? {
                        ...prev,
                        current_bindings: 0,
                        resets_this_month: prev.resets_this_month + 1,
                        resets_remaining: result.resets_remaining_this_month
                    } : null);
                    fetchData();
                } catch (error) {
                    console.error('Failed to reset HWID:', error);
                    const errorMessage = error.response?.data?.detail || 'Failed to reset HWID bindings.';
                    toast.error(errorMessage);
                } finally {
                    setResetting(false);
                }
            }
        });
    };

    const handleRemoveBinding = async (bindingId) => {
        setConfirmDialog({
            isOpen: true,
            title: 'Remove Machine Binding',
            message: 'Are you sure you want to remove this machine binding? The machine will need to re-activate.',
            confirmText: 'Remove',
            confirmVariant: 'danger',
            onConfirm: async () => {
                try {
                    await licenseApi.removeBinding(selectedLicense.id, bindingId);
                    setBindings(bindings.filter(b => b.id !== bindingId));
                    toast.success('Machine binding removed successfully');
                    fetchData();
                } catch (error) {
                    console.error('Failed to remove binding:', error);
                    toast.error('Failed to remove machine binding');
                }
            }
        });
    };

    const getStatusBadge = (status) => {
        switch (status) {
            case 'active':
                return (
                    <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle size={12} /> Active
                    </span>
                );
            case 'revoked':
                return (
                    <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                        <XCircle size={12} /> Revoked
                    </span>
                );
            default:
                return (
                    <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        <AlertTriangle size={12} /> {status}
                    </span>
                );
        }
    };

    return (
        <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Licenses</h1>
                    <p className="text-slate-400">Issue and manage access keys.</p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleExportCSV}
                        className="btn btn-secondary"
                        title="Export to CSV"
                    >
                        <Download size={18} />
                        Export CSV
                    </button>
                    <button onClick={() => setIsModalOpen(true)} className="btn btn-primary">
                        <Plus size={20} />
                        Issue License
                    </button>
                </div>
            </div>

            {/* Search and Filters */}
            <div className="glass-card p-4 mb-6">
                <div className="flex flex-wrap items-center gap-4">
                    <div className="flex items-center gap-3 flex-1 min-w-[200px]">
                        <Search size={20} className="text-slate-400" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search by key, client name or email..."
                            className="input flex-1 w-auto bg-slate-900/50"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <Filter size={16} className="text-slate-400" />
                        <select
                            value={filterProject}
                            onChange={(e) => setFilterProject(e.target.value)}
                            className="input bg-slate-900/50"
                        >
                            <option value="">All Projects</option>
                            {projects.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                        <select
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                            className="input bg-slate-900/50"
                        >
                            <option value="">All Status</option>
                            <option value="active">Active</option>
                            <option value="revoked">Revoked</option>
                            <option value="expired">Expired</option>
                        </select>
                    </div>
                </div>

                {/* Bulk Actions Bar */}
                {selectedLicenses.size > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
                        <span className="text-sm text-slate-400">
                            {selectedLicenses.size} license(s) selected
                        </span>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleBulkRevoke}
                                className="btn btn-secondary text-amber-400 hover:bg-amber-500/10"
                            >
                                <Ban size={16} />
                                Revoke Selected
                            </button>
                            <button
                                onClick={handleBulkDelete}
                                className="btn btn-secondary text-red-400 hover:bg-red-500/10"
                            >
                                <Trash2 size={16} />
                                Delete Selected
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <div className="glass-card overflow-hidden">
                <div className="table-container border-0 bg-transparent">
                    <table>
                        <thead>
                            <tr>
                                <th className="w-12">
                                    <input
                                        type="checkbox"
                                        checked={selectedLicenses.size === paginatedLicenses.length && paginatedLicenses.length > 0}
                                        onChange={handleSelectAll}
                                        className="rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500"
                                    />
                                </th>
                                <th>License Key</th>
                                <th>Project</th>
                                <th>Client Details</th>
                                <th>Status</th>
                                <th>Expires</th>
                                <th>Usage</th>
                                <th>Features</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginatedLicenses.length === 0 ? (
                                <tr>
                                    <td colSpan="9" className="text-center py-12 text-slate-500">
                                        {loading ? 'Loading...' : 'No licenses found.'}
                                    </td>
                                </tr>
                            ) : (
                                paginatedLicenses.map((license, index) => (
                                    <tr key={license.id} className="group hover:bg-white/5 transition-colors animate-fade-in" style={{ animationDelay: `${index * 50}ms` }}>
                                        <td>
                                            <input
                                                type="checkbox"
                                                checked={selectedLicenses.has(license.id)}
                                                onChange={() => handleSelectLicense(license.id)}
                                                className="rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500"
                                            />
                                        </td>
                                        <td className="font-mono text-sm">
                                            <div className="flex items-center gap-3">
                                                <div className="p-2 rounded bg-white/5 text-slate-400">
                                                    <Key size={14} />
                                                </div>
                                                <span className="text-indigo-300 font-medium">{license.license_key}</span>
                                                <button
                                                    onClick={() => copyToClipboard(license.license_key)}
                                                    className="text-slate-500 hover:text-white opacity-0 group-hover:opacity-100 transition-all"
                                                    title="Copy Key"
                                                >
                                                    <Copy size={14} />
                                                </button>
                                            </div>
                                        </td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <Folder size={14} className="text-blue-400" />
                                                <span className="text-sm text-slate-300">{getProjectName(license)}</span>
                                            </div>
                                        </td>
                                        <td>
                                            <div className="flex flex-col">
                                                <span className="font-medium text-white">{license.client_name || 'Unknown Client'}</span>
                                                <span className="text-xs text-slate-500">{license.client_email || 'No email'}</span>
                                            </div>
                                        </td>
                                        <td>
                                            {getStatusBadge(license.status)}
                                        </td>
                                        <td>
                                            {license.expires_at ? (
                                                <div className="flex items-center gap-2">
                                                    <Calendar size={14} className={(() => {
                                                        const daysUntilExpiry = Math.ceil((new Date(license.expires_at) - new Date()) / (1000 * 60 * 60 * 24));
                                                        if (daysUntilExpiry < 0) return 'text-red-400';
                                                        if (daysUntilExpiry < 7) return 'text-red-400';
                                                        if (daysUntilExpiry < 30) return 'text-amber-400';
                                                        return 'text-slate-400';
                                                    })()} />
                                                    <span className={(() => {
                                                        const daysUntilExpiry = Math.ceil((new Date(license.expires_at) - new Date()) / (1000 * 60 * 60 * 24));
                                                        if (daysUntilExpiry < 0) return 'text-red-400';
                                                        if (daysUntilExpiry < 7) return 'text-red-400';
                                                        if (daysUntilExpiry < 30) return 'text-amber-400';
                                                        return 'text-slate-400';
                                                    })()}>
                                                        {new Date(license.expires_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                            ) : (
                                                <span className="text-slate-500 text-sm">Never</span>
                                            )}
                                        </td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-indigo-500 rounded-full"
                                                        style={{ width: `${(license.active_machines / license.max_machines) * 100}%` }}
                                                    />
                                                </div>
                                                <span className="text-xs text-slate-400">
                                                    {license.active_machines}/{license.max_machines}
                                                </span>
                                            </div>
                                        </td>
                                        <td>
                                            <div className="flex flex-wrap gap-1 max-w-[150px]">
                                                {(license.features || []).slice(0, 2).map((feature, i) => (
                                                    <span key={i} className="px-2 py-0.5 text-xs bg-indigo-500/20 text-indigo-300 rounded-full">
                                                        {feature}
                                                    </span>
                                                ))}
                                                {(license.features || []).length > 2 && (
                                                    <span className="px-2 py-0.5 text-xs bg-slate-500/20 text-slate-400 rounded-full">
                                                        +{license.features.length - 2}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td>
                                            <div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => handleViewBindings(license)}
                                                    className="p-2 rounded-lg hover:bg-indigo-500/20 text-slate-400 hover:text-indigo-400 transition-colors"
                                                    title="View Machines"
                                                >
                                                    <Monitor size={16} />
                                                </button>
                                                {license.status === 'active' && (
                                                    <button
                                                        onClick={() => handleRevoke(license.id)}
                                                        className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                                                        title="Revoke License"
                                                    >
                                                        <Ban size={16} />
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleDelete(license.id)}
                                                    className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                                                    title="Delete License"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-white/10">
                        <span className="text-sm text-slate-400">
                            Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredLicenses.length)} of {filteredLicenses.length} licenses
                        </span>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronLeft size={18} />
                            </button>
                            {[...Array(totalPages)].map((_, i) => (
                                <button
                                    key={i + 1}
                                    onClick={() => setCurrentPage(i + 1)}
                                    className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${currentPage === i + 1
                                        ? 'bg-indigo-500 text-white'
                                        : 'hover:bg-white/10 text-slate-400'
                                        }`}
                                >
                                    {i + 1}
                                </button>
                            )).slice(
                                Math.max(0, currentPage - 3),
                                Math.min(totalPages, currentPage + 2)
                            )}
                            <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                <ChevronRight size={18} />
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* Create License Modal */}
            <CreateLicenseModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                projects={projects}
                newLicense={newLicense}
                setNewLicense={setNewLicense}
                featureInput={featureInput}
                setFeatureInput={setFeatureInput}
                onSubmit={handleCreate}
                onAddFeature={handleAddFeature}
                onRemoveFeature={handleRemoveFeature}
            />

            {/* Bindings Modal */}
            <BindingsModal
                isOpen={isBindingsModalOpen}
                onClose={() => {
                    setIsBindingsModalOpen(false);
                    setSelectedLicense(null);
                    setBindings([]);
                    setResetStatus(null);
                }}
                license={selectedLicense}
                bindings={bindings}
                bindingsLoading={bindingsLoading}
                resetStatus={resetStatus}
                resetting={resetting}
                onResetHwid={handleResetHwid}
                onRemoveBinding={handleRemoveBinding}
            />

            {/* Confirm Dialog */}
            <ConfirmDialog
                isOpen={confirmDialog.isOpen}
                onClose={() => setConfirmDialog(prev => ({ ...prev, isOpen: false }))}
                onConfirm={confirmDialog.onConfirm}
                title={confirmDialog.title}
                message={confirmDialog.message}
                confirmText={confirmDialog.confirmText}
                confirmVariant={confirmDialog.confirmVariant}
            />
        </div>
    );
};

export default Licenses;

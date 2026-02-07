import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
    Users, Database, Key, Activity, CheckCircle, RefreshCw,
    Shield, TrendingUp, Server, Globe, ArrowLeft, DollarSign,
    Zap, Crown, AlertTriangle, Search, Ban
} from 'lucide-react';
import { admin } from '../services/api';
import { useToast } from '../components/Toast';
import { SkeletonCard, SkeletonChart } from '../components/Skeleton';
import ConfirmDialog from '../components/ConfirmDialog';
import StatCard from '../components/dashboard/StatCard';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';

// Status indicator component
const StatusIndicator = ({ status, size = 'md' }) => {
    const sizeClass = size === 'sm' ? 'h-2 w-2' : 'h-3 w-3';
    const colorClass = status === 'healthy' ? 'bg-emerald-500' :
                       status === 'warning' ? 'bg-amber-500' : 'bg-red-500';
    return <span className={`${sizeClass} rounded-full ${colorClass} animate-pulse`} />;
};

const AdminDashboard = () => {
    const [stats, setStats] = useState(null);
    const [users, setUsers] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [revenue, setRevenue] = useState(null);
    const [systemHealth, setSystemHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const [userSearch, setUserSearch] = useState('');
    const [actionLoading, setActionLoading] = useState(null);
    const [banConfirm, setBanConfirm] = useState({ open: false, userId: null, email: '' });
    const { showToast } = useToast();

    const tabs = [
        { id: 'overview', label: 'Overview', icon: Activity },
        { id: 'revenue', label: 'Revenue', icon: DollarSign },
        { id: 'users', label: 'Users', icon: Users },
        { id: 'system', label: 'System Health', icon: Server },
        { id: 'webhooks', label: 'Webhooks', icon: Globe },
    ];

    const fetchData = async () => {
        setLoading(true);
        try {
            const [statsData, usersData, analyticsData, revenueData, healthData] = await Promise.all([
                admin.getStats(),
                admin.getUsers(),
                admin.getAnalytics(30),
                admin.getRevenue().catch(() => null),
                admin.getSystemHealth().catch(() => null),
            ]);
            setStats(statsData);
            setUsers(usersData);
            setAnalytics(analyticsData);
            setRevenue(revenueData);
            setSystemHealth(healthData);
        } catch (error) {
            console.error('Failed to fetch admin data:', error);
            showToast('Failed to load admin data. Please try again.', 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleUpdatePlan = async (userId, newPlan) => {
        setActionLoading(userId);
        try {
            await admin.updateUserPlan(userId, newPlan);
            showToast(`User plan updated to ${newPlan}`, 'success');
            // Refresh users list
            const usersData = await admin.getUsers();
            setUsers(usersData);
        } catch (error) {
            showToast('Failed to update user plan', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const handleUpdateRole = async (userId, newRole) => {
        setActionLoading(userId);
        try {
            await admin.updateUserRole(userId, newRole);
            showToast(`User role updated to ${newRole}`, 'success');
            const usersData = await admin.getUsers();
            setUsers(usersData);
        } catch (error) {
            showToast('Failed to update user role', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const handleBanUser = async (userId, email) => {
        setBanConfirm({ open: true, userId, email });
    };

    const confirmBanUser = async () => {
        const { userId, email } = banConfirm;
        setBanConfirm({ open: false, userId: null, email: '' });
        setActionLoading(userId);

        try {
            await admin.banUser(userId);
            showToast(`User ${email} has been banned`, 'success');
            const usersData = await admin.getUsers();
            setUsers(usersData);
        } catch (error) {
            showToast(error.response?.data?.detail || 'Failed to ban user', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const filteredUsers = users.filter(user =>
        user.email?.toLowerCase().includes(userSearch.toLowerCase()) ||
        user.name?.toLowerCase().includes(userSearch.toLowerCase())
    );

    // Pie chart colors
    const PLAN_COLORS = {
        free: '#64748b',
        pro: '#8b5cf6',
        business: '#f59e0b',
    };

    if (loading) return (
        <div className="space-y-6 animate-fade-in">
            <div className="flex items-end justify-between border-b border-white/10 pb-6">
                <div>
                    <div className="h-8 w-48 bg-white/5 rounded animate-pulse mb-2" />
                    <div className="h-4 w-64 bg-white/5 rounded animate-pulse" />
                </div>
                <div className="h-10 w-24 bg-white/5 rounded-lg animate-pulse" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
            </div>
            <SkeletonChart />
        </div>
    );

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between border-b border-white/10 pb-6">
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <Shield className="text-amber-400" size={28} />
                        <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
                    </div>
                    <p className="text-slate-400 text-sm">System-wide statistics and user management</p>
                </div>
                <div className="flex items-center gap-3">
                    <Link to="/" className="btn-secondary flex items-center gap-2">
                        <ArrowLeft size={16} />
                        User Dashboard
                    </Link>
                    <button onClick={fetchData} className="btn-secondary flex items-center gap-2">
                        <RefreshCw size={16} />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Total Users"
                    value={stats?.total_users || 0}
                    icon={Users}
                    color="from-blue-500 to-blue-600"
                />
                <StatCard
                    title="Total Projects"
                    value={stats?.total_projects || 0}
                    icon={Database}
                    color="from-violet-500 to-violet-600"
                />
                <StatCard
                    title="Total Licenses"
                    value={stats?.total_licenses || 0}
                    icon={Key}
                    color="from-emerald-500 to-emerald-600"
                    subtitle={`${stats?.active_licenses || 0} active`}
                />
                <StatCard
                    title="Validations Today"
                    value={stats?.validations_today || 0}
                    icon={Activity}
                    color="from-amber-500 to-amber-600"
                    subtitle={`${stats?.validations_week || 0} this week`}
                />
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-white/10 pb-2 overflow-x-auto">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors whitespace-nowrap ${activeTab === tab.id
                            ? 'bg-primary/20 text-primary border border-primary/30'
                            : 'text-slate-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'overview' && (
                <div className="space-y-6">
                    {/* Secondary Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <StatCard
                            title="Total Compilations"
                            value={stats?.total_compiles || 0}
                            icon={Server}
                            color="from-pink-500 to-pink-600"
                            subtitle={`${stats?.successful_compiles || 0} successful`}
                        />
                        <StatCard
                            title="Success Rate"
                            value={stats?.total_compiles > 0
                                ? `${Math.round((stats?.successful_compiles / stats?.total_compiles) * 100)}%`
                                : 'N/A'}
                            icon={TrendingUp}
                            color="from-cyan-500 to-cyan-600"
                        />
                    </div>

                    {/* Validations Chart */}
                    <div className="glass-card p-6">
                        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Activity size={20} className="text-amber-400" />
                            Validation Activity (Last 30 Days)
                        </h2>
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={100}>
                                <AreaChart data={analytics?.validations || []}>
                                    <defs>
                                        <linearGradient id="validationGradient" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                    <XAxis
                                        dataKey="date"
                                        stroke="#64748b"
                                        tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                    />
                                    <YAxis stroke="#64748b" />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                        labelStyle={{ color: '#f1f5f9' }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="count"
                                        stroke="#f59e0b"
                                        fill="url(#validationGradient)"
                                        strokeWidth={2}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* New Users Chart */}
                    <div className="glass-card p-6">
                        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Users size={20} className="text-blue-400" />
                            New Users (Last 30 Days)
                        </h2>
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={100}>
                                <LineChart data={analytics?.new_users || []}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                    <XAxis
                                        dataKey="date"
                                        stroke="#64748b"
                                        tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                    />
                                    <YAxis stroke="#64748b" />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                        labelStyle={{ color: '#f1f5f9' }}
                                    />
                                    <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'revenue' && (
                <div className="space-y-6">
                    {/* Revenue Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <StatCard
                            title="Monthly Recurring Revenue"
                            value={`$${revenue?.mrr || 0}`}
                            icon={DollarSign}
                            color="from-emerald-500 to-emerald-600"
                        />
                        <StatCard
                            title="Pro Subscribers"
                            value={revenue?.pro_subscribers || 0}
                            icon={Zap}
                            color="from-violet-500 to-violet-600"
                            subtitle="$15/month each"
                        />
                        <StatCard
                            title="Business Subscribers"
                            value={revenue?.business_subscribers || 0}
                            icon={Crown}
                            color="from-amber-500 to-amber-600"
                            subtitle="$39/month each"
                        />
                    </div>

                    {/* Users by Plan Breakdown */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="glass-card p-6">
                            <h2 className="text-lg font-semibold text-white mb-4">Users by Plan</h2>
                            <div className="h-64 flex items-center justify-center">
                                {revenue?.users_by_plan?.length > 0 ? (
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={revenue.users_by_plan}
                                                dataKey="count"
                                                nameKey="plan"
                                                cx="50%"
                                                cy="50%"
                                                outerRadius={80}
                                                label={({ plan, count }) => `${plan}: ${count}`}
                                            >
                                                {revenue.users_by_plan.map((entry, index) => (
                                                    <Cell key={index} fill={PLAN_COLORS[entry.plan] || '#64748b'} />
                                                ))}
                                            </Pie>
                                            <Tooltip
                                                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                            />
                                        </PieChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <p className="text-slate-400">No subscription data available</p>
                                )}
                            </div>
                        </div>

                        <div className="glass-card p-6">
                            <h2 className="text-lg font-semibold text-white mb-4">Plan Breakdown</h2>
                            <div className="space-y-4">
                                {revenue?.users_by_plan?.map(item => (
                                    <div key={item.plan} className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div
                                                className="w-4 h-4 rounded-full"
                                                style={{ backgroundColor: PLAN_COLORS[item.plan] || '#64748b' }}
                                            />
                                            <span className="text-white capitalize font-medium">{item.plan}</span>
                                        </div>
                                        <span className="text-slate-300">{item.count} users</span>
                                    </div>
                                )) || (
                                    <p className="text-slate-400">No data available</p>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {activeTab === 'users' && (
                <div className="glass-card overflow-hidden">
                    <div className="p-4 border-b border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <Users size={20} className="text-blue-400" />
                            All Users ({filteredUsers.length})
                        </h2>
                        <div className="relative w-full sm:w-64">
                            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search by email or name..."
                                value={userSearch}
                                onChange={(e) => setUserSearch(e.target.value)}
                                className="w-full pl-9 pr-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary/50"
                            />
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-white/10 bg-white/5">
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Email</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Name</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Role</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Plan</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Projects</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Licenses</th>
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredUsers.map(user => (
                                    <tr key={user.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                        <td className="p-4 text-sm text-white">{user.email}</td>
                                        <td className="p-4 text-sm text-slate-300">{user.name || '-'}</td>
                                        <td className="p-4">
                                            <select
                                                value={user.role || 'user'}
                                                onChange={(e) => handleUpdateRole(user.id, e.target.value)}
                                                disabled={actionLoading === user.id || user.role === 'banned'}
                                                className={`px-2 py-1 text-xs font-medium rounded bg-slate-700 border border-slate-600 cursor-pointer ${
                                                    user.role === 'admin' ? 'text-amber-400' :
                                                    user.role === 'banned' ? 'text-red-400' : 'text-slate-300'
                                                } disabled:opacity-50`}
                                            >
                                                <option value="user">User</option>
                                                <option value="admin">Admin</option>
                                                {user.role === 'banned' && <option value="banned">Banned</option>}
                                            </select>
                                        </td>
                                        <td className="p-4">
                                            <select
                                                value={user.plan || 'free'}
                                                onChange={(e) => handleUpdatePlan(user.id, e.target.value)}
                                                disabled={actionLoading === user.id || user.role === 'banned'}
                                                className={`px-2 py-1 text-xs font-medium rounded bg-slate-700 border border-slate-600 cursor-pointer ${
                                                    user.plan === 'business' ? 'text-amber-400' :
                                                    user.plan === 'pro' ? 'text-violet-400' : 'text-slate-300'
                                                } disabled:opacity-50`}
                                            >
                                                <option value="free">Free</option>
                                                <option value="pro">Pro</option>
                                                <option value="business">Business</option>
                                            </select>
                                        </td>
                                        <td className="p-4 text-sm text-slate-300">{user.project_count}</td>
                                        <td className="p-4 text-sm text-slate-300">{user.license_count}</td>
                                        <td className="p-4">
                                            {user.role !== 'banned' && (
                                                <button
                                                    onClick={() => handleBanUser(user.id, user.email)}
                                                    disabled={actionLoading === user.id}
                                                    className="flex items-center gap-1 px-2 py-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
                                                >
                                                    <Ban size={12} />
                                                    Ban
                                                </button>
                                            )}
                                            {user.role === 'banned' && (
                                                <span className="text-xs text-red-400 font-medium">Banned</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {activeTab === 'system' && (
                <div className="space-y-6">
                    {/* System Status Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="glass-card p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm text-slate-400">Database Pool</span>
                                <StatusIndicator
                                    status={systemHealth?.database?.free_size > 0 ? 'healthy' : 'warning'}
                                />
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {(systemHealth?.database?.size || 0) - (systemHealth?.database?.free_size || 0)}/{systemHealth?.database?.max_size || 0}
                            </p>
                            <p className="text-xs text-slate-500">connections in use</p>
                        </div>

                        <div className="glass-card p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm text-slate-400">Webhook Success</span>
                                <StatusIndicator
                                    status={
                                        (systemHealth?.webhooks?.success_rate || 100) >= 95 ? 'healthy' :
                                        (systemHealth?.webhooks?.success_rate || 100) >= 80 ? 'warning' : 'error'
                                    }
                                />
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {systemHealth?.webhooks?.success_rate || 100}%
                            </p>
                            <p className="text-xs text-slate-500">last 24 hours</p>
                        </div>

                        <div className="glass-card p-4">
                            <span className="text-sm text-slate-400">Webhooks (24h)</span>
                            <p className="text-2xl font-bold text-white mt-2">
                                {systemHealth?.webhooks?.total_24h || 0}
                            </p>
                            <p className="text-xs text-slate-500">deliveries</p>
                        </div>

                        <div className="glass-card p-4">
                            <span className="text-sm text-slate-400">Validations/Hour</span>
                            <p className="text-2xl font-bold text-white mt-2">
                                {systemHealth?.api_performance?.validations_last_hour || 0}
                            </p>
                            <p className="text-xs text-slate-500">license checks</p>
                        </div>
                    </div>

                    {/* Recent Errors */}
                    <div className="glass-card p-6">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <AlertTriangle className="text-red-400" size={20} />
                            Recent Compile Errors
                        </h3>
                        {systemHealth?.recent_errors?.length > 0 ? (
                            <div className="space-y-2">
                                {systemHealth.recent_errors.map(error => (
                                    <div key={error.id} className="p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                                        <p className="text-sm text-red-300 font-mono break-all">{error.message}</p>
                                        <p className="text-xs text-slate-500 mt-1">
                                            {error.timestamp ? new Date(error.timestamp).toLocaleString() : 'Unknown time'}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-8">
                                <CheckCircle className="mx-auto text-emerald-400 mb-2" size={32} />
                                <p className="text-slate-400 text-sm">No recent errors</p>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {activeTab === 'webhooks' && (
                <div className="glass-card p-6">
                    <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Globe size={20} className="text-violet-400" />
                        Recent Webhook Deliveries
                    </h2>
                    {analytics?.recent_webhooks?.length > 0 ? (
                        <div className="space-y-2">
                            {analytics.recent_webhooks.map(webhook => (
                                <div key={webhook.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        {webhook.success ? (
                                            <CheckCircle size={16} className="text-emerald-400" />
                                        ) : (
                                            <AlertTriangle size={16} className="text-red-400" />
                                        )}
                                        <div>
                                            <p className="text-sm text-white font-medium">{webhook.event_type}</p>
                                            <p className="text-xs text-slate-500">{webhook.webhook_name}</p>
                                        </div>
                                    </div>
                                    <span className="text-xs text-slate-500">
                                        {webhook.created_at ? new Date(webhook.created_at).toLocaleString() : '-'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-slate-400 text-sm">No recent webhook deliveries</p>
                    )}
                </div>
            )}

            {/* Ban User Confirmation Dialog */}
            <ConfirmDialog
                open={banConfirm.open}
                title="Ban User"
                message={`Are you sure you want to ban ${banConfirm.email}? This will revoke all their licenses.`}
                onConfirm={confirmBanUser}
                onCancel={() => setBanConfirm({ open: false, userId: null, email: '' })}
            />
        </div>
    );
};

export default AdminDashboard;

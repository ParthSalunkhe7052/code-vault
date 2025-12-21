import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
    Users, Database, Key, Activity, CheckCircle, RefreshCw,
    Shield, TrendingUp, Server, Globe, ArrowLeft
} from 'lucide-react';
import { admin } from '../services/api';
import { useToast } from '../components/Toast';
import { SkeletonCard, SkeletonChart } from '../components/Skeleton';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

// StatCard component - moved outside to prevent recreation on every render
const StatCard = ({ title, value, icon: Icon, color, subtitle }) => (
    <div className="glass-card p-6 hover:scale-[1.02] transition-transform cursor-default">
        <div className="flex items-start justify-between">
            <div>
                <p className="text-slate-400 text-sm font-medium">{title}</p>
                <p className="text-3xl font-bold text-white mt-1">{value}</p>
                {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
            </div>
            <div className={`p-3 rounded-xl bg-gradient-to-br ${color} shadow-lg`}>
                <Icon size={24} className="text-white" />
            </div>
        </div>
    </div>
);

const AdminDashboard = () => {
    const [stats, setStats] = useState(null);
    const [users, setUsers] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const { showToast } = useToast();

    const fetchData = async () => {
        setLoading(true);
        try {
            const [statsData, usersData, analyticsData] = await Promise.all([
                admin.getStats(),
                admin.getUsers(),
                admin.getAnalytics(30)
            ]);
            setStats(statsData);
            setUsers(usersData);
            setAnalytics(analyticsData);
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

            {/* Tabs */}
            <div className="flex gap-2 border-b border-white/10 pb-2">
                {['overview', 'users', 'webhooks'].map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${activeTab === tab
                            ? 'bg-primary/20 text-primary border border-primary/30'
                            : 'text-slate-400 hover:text-white hover:bg-white/5'
                            }`}
                    >
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'overview' && (
                <div className="space-y-6">
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

            {activeTab === 'users' && (
                <div className="glass-card overflow-hidden">
                    <div className="p-4 border-b border-white/10">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <Users size={20} className="text-blue-400" />
                            All Users ({users.length})
                        </h2>
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
                                    <th className="text-left p-4 text-sm font-medium text-slate-400">Joined</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map(user => (
                                    <tr key={user.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                        <td className="p-4 text-sm text-white">{user.email}</td>
                                        <td className="p-4 text-sm text-slate-300">{user.name || '-'}</td>
                                        <td className="p-4">
                                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${user.role === 'admin'
                                                    ? 'bg-amber-500/20 text-amber-400'
                                                    : 'bg-slate-500/20 text-slate-400'
                                                }`}>
                                                {user.role}
                                            </span>
                                        </td>
                                        <td className="p-4 text-sm text-slate-300">{user.plan}</td>
                                        <td className="p-4 text-sm text-slate-300">{user.project_count}</td>
                                        <td className="p-4 text-sm text-slate-300">{user.license_count}</td>
                                        <td className="p-4 text-sm text-slate-500">
                                            {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
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
                                            <Activity size={16} className="text-red-400" />
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
        </div>
    );
};

export default AdminDashboard;

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Database, Key, CheckCircle, RefreshCw, AlertTriangle, ArrowRight } from 'lucide-react';
import { stats } from '../services/api';
import { StatCard, ActivityItem, ExpiringLicense, ValidationChart, MachinesList, LiveMap } from '../components/dashboard';
import { SkeletonCard, SkeletonList, SkeletonChart } from '../components/Skeleton';
import Spinner from '../components/Spinner';

const Dashboard = () => {
    const [dashboardStats, setDashboardStats] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        setLoading(true);
        try {
            const data = await stats.getDashboard();
            setDashboardStats(data);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    if (loading) return (
        <div className="space-y-6 animate-fade-in">
            {/* Header Skeleton */}
            <div className="flex items-end justify-between border-b border-white/10 pb-6">
                <div>
                    <div className="h-8 w-32 bg-white/5 rounded animate-pulse mb-2" />
                    <div className="h-4 w-48 bg-white/5 rounded animate-pulse" />
                </div>
                <div className="h-10 w-24 bg-white/5 rounded-lg animate-pulse" />
            </div>

            {/* Stats Grid Skeleton */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[...Array(4)].map((_, i) => (
                    <SkeletonCard key={i} />
                ))}
            </div>

            {/* Two Column Layout Skeleton */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass-card p-6">
                    <div className="h-6 w-40 bg-white/5 rounded animate-pulse mb-4" />
                    <SkeletonList items={4} />
                </div>
                <div className="glass-card p-6">
                    <div className="h-6 w-40 bg-white/5 rounded animate-pulse mb-4" />
                    <SkeletonList items={4} />
                </div>
            </div>

            {/* Chart Skeleton */}
            <SkeletonChart />
        </div>
    );

    const validationSuccessRate = dashboardStats?.validations?.last_24h?.total > 0
        ? Math.round((dashboardStats.validations.last_24h.successful / dashboardStats.validations.last_24h.total) * 100)
        : 100;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between border-b border-white/10 pb-6">
                <div>
                    <h1 className="text-2xl font-bold text-white mb-1">Dashboard</h1>
                    <p className="text-slate-400 text-sm">Overview of your license management</p>
                </div>
                <button
                    onClick={fetchData}
                    className="btn-secondary flex items-center gap-2"
                >
                    <RefreshCw size={16} />
                    Refresh
                </button>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Link to="/projects">
                    <StatCard
                        title="Projects"
                        value={dashboardStats?.projects || 0}
                        icon={Database}
                        color="text-blue-400"
                        subtitle="Click to manage"
                    />
                </Link>

                <Link to="/licenses">
                    <StatCard
                        title="Total Licenses"
                        value={dashboardStats?.licenses?.total || 0}
                        icon={Key}
                        color="text-violet-400"
                        subtitle="Click to manage"
                    />
                </Link>

                <StatCard
                    title="Active Licenses"
                    value={dashboardStats?.licenses?.active || 0}
                    icon={CheckCircle}
                    color="text-emerald-400"
                />

                <StatCard
                    title="Validations (24h)"
                    value={dashboardStats?.validations?.last_24h?.total || 0}
                    icon={Activity}
                    color="text-amber-400"
                    subtitle={`${validationSuccessRate}% success rate`}
                />
            </div>

            {/* Mission Control Live Map */}
            <LiveMap />

            {/* Alerts Section */}
            {dashboardStats?.expiring_soon?.length > 0 && (
                <div className="glass-card p-6 border-amber-500/20 bg-amber-500/5">
                    <div className="flex items-center gap-3 mb-4">
                        <AlertTriangle size={20} className="text-amber-400" />
                        <h2 className="text-lg font-semibold text-white">Licenses Expiring Soon</h2>
                        <span className="px-2 py-0.5 text-xs font-medium bg-amber-500/20 text-amber-400 rounded-full">
                            {dashboardStats.expiring_soon.length}
                        </span>
                    </div>
                    <div className="divide-y divide-white/5">
                        {dashboardStats.expiring_soon.map((license, i) => (
                            <ExpiringLicense key={license.id || i} license={license} />
                        ))}
                    </div>
                    <Link to="/licenses" className="flex items-center gap-2 text-sm text-amber-400 hover:text-amber-300 mt-4">
                        View all licenses
                        <ArrowRight size={14} />
                    </Link>
                </div>
            )}

            {/* Two Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent Activity */}
                <div className="glass-card p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Activity size={20} className="text-indigo-400" />
                            <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
                        </div>
                    </div>
                    {dashboardStats?.recent_activity?.length > 0 ? (
                        <div className="divide-y divide-white/5">
                            {dashboardStats.recent_activity.slice(0, 6).map((activity, i) => (
                                <ActivityItem key={i} activity={activity} />
                            ))}
                        </div>
                    ) : (
                        <div className="p-4 bg-gradient-to-br from-indigo-500/5 to-violet-500/5 rounded-xl border border-indigo-500/10">
                            <p className="text-slate-300 font-medium text-sm mb-3">🚀 Get Started</p>
                            <div className="space-y-2">
                                <div className={`flex items-center gap-2 text-xs ${dashboardStats?.projects > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                                    {dashboardStats?.projects > 0 ? '✓' : '○'} Create your first project
                                </div>
                                <div className={`flex items-center gap-2 text-xs ${dashboardStats?.licenses?.total > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                                    {dashboardStats?.licenses?.total > 0 ? '✓' : '○'} Issue a license key
                                </div>
                                <div className={`flex items-center gap-2 text-xs ${dashboardStats?.validations?.last_24h?.total > 0 ? 'text-emerald-400' : 'text-slate-400'}`}>
                                    {dashboardStats?.validations?.last_24h?.total > 0 ? '✓' : '○'} Validate a license from your app
                                </div>
                            </div>
                            <p className="text-slate-500 text-xs mt-3">Activity will appear here as you use the system.</p>
                        </div>
                    )}
                </div>

                {/* Active Machines */}
                <MachinesList machines={dashboardStats?.active_machines} />
            </div>

            {/* Validation Stats Chart */}
            <ValidationChart history={dashboardStats?.validations?.history} />

            {/* Quick Actions */}
            <div className="glass-card p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Link to="/projects" className="btn-secondary justify-center">
                        <Database size={18} />
                        Create Project
                    </Link>
                    <Link to="/licenses" className="btn-secondary justify-center">
                        <Key size={18} />
                        Issue License
                    </Link>
                    <Link to="/settings" className="btn-secondary justify-center">
                        <Activity size={18} />
                        View API Key
                    </Link>
                </div>
            </div>

            {/* Getting Started */}
            <div className="glass-card p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Getting Started</h2>
                <div className="space-y-3 text-sm text-slate-400">
                    <p>1. <strong className="text-white">Create a Project</strong> - Group your licenses by application</p>
                    <p>2. <strong className="text-white">Upload Files</strong> - Add your Python scripts to the project</p>
                    <p>3. <strong className="text-white">Generate Licenses</strong> - Create license keys for your clients</p>
                    <p>4. <strong className="text-white">Compile</strong> - Build protected executables with Nuitka</p>
                    <p>5. <strong className="text-white">Distribute</strong> - Share the compiled binary with your clients</p>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;

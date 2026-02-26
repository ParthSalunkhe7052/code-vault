import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, Database, Key, RefreshCw, AlertTriangle, ArrowRight, CloudLightning } from 'lucide-react';
import { stats, projects } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { StatCard, ActivityItem, ExpiringLicense, ValidationChart, MachinesList, QuickStatsBar } from '../components/dashboard';
import UsageStats from '../components/dashboard/UsageStats';
import OnboardingHero from '../components/dashboard/OnboardingHero';
import { SkeletonCard, SkeletonList, SkeletonChart } from '../components/Skeleton';
import ThemeToggle from '../components/ThemeToggle';

const Dashboard = () => {
    // user is already available from AuthContext — no need for a second getMe() call
    const { user: userProfile } = useAuth();
    const [dashboardStats, setDashboardStats] = useState(null);
    const [projectList, setProjectList] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Fetch each independently so one failure doesn't break the whole dashboard
            const [statsResult, projectsResult] = await Promise.allSettled([
                stats.getDashboard(),
                projects.list()
            ]);
            if (statsResult.status === 'fulfilled') setDashboardStats(statsResult.value);
            if (projectsResult.status === 'fulfilled') setProjectList(projectsResult.value || []);
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

    const projectCount = projectList.length || dashboardStats?.projects || 0;
    const hasNoProjects = projectCount === 0;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between border-b border-cv-border pb-6">
                <div>
                    <h1 className="text-2xl font-bold text-cv-text mb-1">Dashboard</h1>
                    <p className="text-cv-text-muted text-sm">Overview of your license management</p>
                </div>
                <div className="flex items-center gap-2">
                    <ThemeToggle />
                    <button
                        onClick={fetchData}
                        className="btn-secondary flex items-center gap-2"
                    >
                        <RefreshCw size={16} />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Onboarding Hero for new users OR Quick Stats for returning users */}
            {hasNoProjects ? (
                <OnboardingHero />
            ) : (
                <QuickStatsBar
                    projectCount={projectCount}
                    licenseStats={dashboardStats?.licenses}
                    validationStats={dashboardStats?.validations}
                />
            )}

            {/* Stats Grid - Hidden for new users to prioritize onboarding */}
            {!hasNoProjects && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <Link to="/projects">
                        <StatCard
                            title="Projects"
                            value={projectList.length}
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

                    {/* Cloud Build Credits */}
                    <StatCard
                        title="Build Credits"
                        value={userProfile?.build_credits || 0}
                        icon={CloudLightning}
                        color="text-amber-400"
                        subtitle={userProfile?.plan === 'free' ? 'Local builds only' : 'Monthly refill'}
                    />

                    <StatCard
                        title="Validations (24h)"
                        value={dashboardStats?.validations?.last_24h?.total || 0}
                        icon={Activity}
                        color="text-emerald-400"
                        subtitle={`${validationSuccessRate}% success rate`}
                    />
                </div>
            )}

            {/* Usage Stats - Only show if there's activity */}
            {!hasNoProjects && (
                <UsageStats 
                    projectCount={projectList.length} 
                    licenseCount={dashboardStats?.licenses?.total || 0} 
                />
            )}

            {/* Alerts Section */}
            {dashboardStats?.expiring_soon?.length > 0 && (
                <div className="glass-card p-6 border-amber-500/20 bg-amber-500/5">
                    <div className="flex items-center gap-3 mb-4">
                        <AlertTriangle size={20} className="text-amber-400" />
                        <h2 className="text-lg font-semibold text-cv-text">Licenses Expiring Soon</h2>
                        <span className="px-2 py-0.5 text-xs font-medium bg-amber-500/20 text-amber-400 rounded-full">
                            {dashboardStats.expiring_soon.length}
                        </span>
                    </div>
                    <div className="divide-y divide-cv-border-subtle">
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
                            <Activity size={20} className="text-cv-primary" />
                            <h2 className="text-lg font-semibold text-cv-text">Recent Activity</h2>
                        </div>
                    </div>
                    {dashboardStats?.recent_activity?.length > 0 ? (
                        <div className="divide-y divide-cv-border-subtle">
                            {dashboardStats.recent_activity.slice(0, 6).map((activity, i) => (
                                <ActivityItem key={i} activity={activity} />
                            ))}
                        </div>
                    ) : (
                        <div className="p-4 text-center">
                            <p className="text-cv-text-dim text-sm">No license validations yet.</p>
                            <p className="text-cv-text-dim text-xs mt-1">Activity will appear here when clients validate licenses.</p>
                        </div>
                    )}
                </div>

                {/* Active Machines */}
                <MachinesList machines={dashboardStats?.active_machines} />
            </div>

            {/* Validation Stats Chart */}
            <ValidationChart history={dashboardStats?.validations?.history} />

        </div>
    );
};

export default Dashboard;

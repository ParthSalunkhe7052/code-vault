
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LogOut, Activity, Shield, Crown, Zap, Sparkles, LayoutDashboard, Box, Key, Webhook, Settings } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import { useEffect, useState } from 'react';
import backgroundMain from '../assets/background_main.png';
import GlobalBuildStatus from './GlobalBuildStatus';
import api from '../services/api';

const Layout = () => {
    const navigate = useNavigate();
    const { user, isAdmin, logout } = useAuth();
    const [apiOnline, setApiOnline] = useState(null); // null = checking

    useEffect(() => {
        let cancelled = false;
        const checkHealth = async () => {
            try {
                await api.get('/health');
                if (!cancelled) setApiOnline(true);
            } catch {
                if (!cancelled) setApiOnline(false);
            }
        };
        checkHealth();
        const interval = setInterval(checkHealth, 60_000);
        return () => { cancelled = true; clearInterval(interval); };
    }, []);
    const { settings } = useSettings();
    const isDarkMatter = settings.theme === 'dark-matter';

    const userPlan = user?.plan || 'free';
    const PlanIcon = userPlan === 'business' ? Crown : userPlan === 'pro' ? Zap : Sparkles;
    const planColor = userPlan === 'business' ? 'text-amber-400' : userPlan === 'pro' ? 'text-violet-400' : 'text-slate-400';
    const planBg = userPlan === 'business' ? 'bg-amber-500/10 border-amber-500/20' : userPlan === 'pro' ? 'bg-violet-500/10 border-violet-500/20' : 'bg-slate-800 border-white/10';

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const navItems = [
        { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
        { path: '/projects', icon: Box, label: 'Projects' },
        { path: '/licenses', icon: Key, label: 'Access Keys' },
        { path: '/webhooks', icon: Webhook, label: 'Webhooks' },
        { path: '/pricing', icon: Crown, label: 'Pricing' },
        { path: '/settings', icon: Settings, label: 'Settings' },
    ];

    const primaryActiveClass = isDarkMatter
        ? 'bg-cv-primary/10 text-cv-text border-cv-primary/20 shadow-cv-primary-active'
        : 'bg-primary/10 text-white border-primary/20 shadow-[0_0_15px_-5px_rgba(99,102,241,0.3)]';

    return (
        <div className="flex h-screen w-full text-cv-text overflow-hidden font-sans selection:bg-cv-primary/30 selection:text-cv-text bg-cv-bg">
            <a
                href="#main-content"
                className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-4 focus:left-4 focus:px-4 focus:py-2 focus:rounded-lg focus:bg-cv-primary focus:text-cv-text focus:font-semibold focus:text-sm focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-cv-primary"
            >
                Skip to content
            </a>
            <div className="fixed inset-0 bg-black pointer-events-none z-0" />
            <img src={backgroundMain} alt="Background" className={`fixed inset-0 w-full h-full object-cover pointer-events-none mix-blend-screen z-0 ${isDarkMatter ? 'opacity-20' : 'opacity-40'}`} />
            <div className="fixed inset-0 bg-grid-pattern opacity-10 pointer-events-none z-0" />
            <div className="fixed inset-0 pointer-events-none z-0 bg-cv-bottom-fade" />

            <aside className="w-72 flex flex-col border-r backdrop-blur-xl relative z-20 border-cv-border bg-cv-card">
                <div className="p-6 border-b border-cv-border">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-cv-primary-glow animate-pulse-slow bg-cv-primary-gradient">
                            <Activity size={22} />
                        </div>
                        <div>
                            <h1 className="font-bold text-lg tracking-wider uppercase text-cv-text">CodeVault</h1>
                            <p className="text-[10px] font-mono tracking-widest text-cv-primary">SYSTEM V2.0</p>
                        </div>
                    </div>
                </div>

                <nav aria-label="Main navigation" className="flex-1 p-4 space-y-2 overflow-y-auto">
                    <div className="px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-cv-text-muted">
                        Mission Control
                    </div>
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/'}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-4 py-3 rounded-xl relative overflow-hidden border transition-all duration-150 ease-in-out ${isActive
                                    ? primaryActiveClass
                                    : 'border-transparent text-cv-text-muted hover:bg-cv-border-subtle hover:border-cv-border hover:text-cv-text'
                                }`
                            }
                        >
                            {({ isActive }) => (
                                <>
                                    <div className="w-8 h-8 flex items-center justify-center">
                                        <item.icon size={20} />
                                    </div>
                                    <span className="font-medium tracking-wide">{item.label}</span>
                                    {isActive && (
                                        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-l-full bg-cv-primary shadow-cv-primary-glow-strong" />
                                    )}
                                </>
                            )}
                        </NavLink>
                    ))}

                    {isAdmin && (
                        <>
                            <div className="mt-6 px-4 py-2 text-[10px] font-bold text-amber-500/70 uppercase tracking-widest">
                                Admin
                            </div>
                            <NavLink
                                to="/admin"
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-4 py-3 rounded-xl relative overflow-hidden border transition-all duration-150 ease-in-out ${isActive
                                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-cv-amber-active'
                                        : 'border-transparent text-cv-text-muted hover:bg-cv-border-subtle hover:border-cv-border hover:text-cv-text'
                                    }`
                                }
                            >
                                {({ isActive }) => (
                                    <>
                                        <div className="w-8 h-8 flex items-center justify-center">
                                            <Shield size={20} className="text-amber-400" />
                                        </div>
                                        <span className="font-medium tracking-wide">Admin Dashboard</span>
                                        {isActive && (
                                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-amber-500 rounded-l-full shadow-cv-amber-strong" />
                                        )}
                                    </>
                                )}
                            </NavLink>
                        </>
                    )}

                    <div className="mt-6 px-4 py-2 text-[10px] font-bold text-purple-500/70 uppercase tracking-widest">
                        Build Tools
                    </div>
                    <NavLink
                        to="/build-settings"
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-3 rounded-xl relative overflow-hidden border transition-all duration-150 ease-in-out ${isActive
                                ? 'bg-purple-500/10 text-purple-400 border-purple-500/20 shadow-cv-purple-active'
                                : 'border-transparent text-cv-text-muted hover:bg-cv-border-subtle hover:border-cv-border hover:text-cv-text'
                            }`
                        }
                    >
                        {({ isActive }) => (
                            <>
                                <div className="w-8 h-8 flex items-center justify-center">
                                    <Activity size={20} className="text-purple-400" />
                                </div>
                                <span className="font-medium tracking-wide">Build Settings</span>
                                {isActive && (
                                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-purple-500 rounded-l-full shadow-cv-purple-strong" />
                                )}
                            </>
                        )}
                    </NavLink>

                    <div className="mt-8 px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-cv-text-muted">
                        System Status
                    </div>
                    <div className="px-4 py-3 rounded-xl border mx-2 bg-cv-bg-elevated border-cv-border">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs text-cv-text-muted">API Server</span>
                            {apiOnline === null && (
                                <span className="text-xs text-cv-text-dim font-mono">CHECKING</span>
                            )}
                            {apiOnline === true && (
                                <span className="text-xs text-emerald-400 font-mono">ONLINE</span>
                            )}
                            {apiOnline === false && (
                                <span className="text-xs text-red-400 font-mono">OFFLINE</span>
                            )}
                        </div>
                        <div className="w-full h-1 rounded-full overflow-hidden bg-cv-muted">
                            {apiOnline === null && (
                                <div className="h-full w-1/2 bg-cv-text-dim animate-pulse" />
                            )}
                            {apiOnline === true && (
                                <div className="h-full w-full bg-emerald-500 shadow-cv-emerald-pulse animate-pulse" />
                            )}
                            {apiOnline === false && (
                                <div className="h-full w-full bg-red-500" />
                            )}
                        </div>
                    </div>
                </nav>

                <div className="p-4 border-t border-cv-border bg-cv-bg-secondary">
                    <div className="mb-4 flex items-center gap-3 px-2">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${planBg}`}>
                            <PlanIcon size={20} className={planColor} />
                        </div>
                        <div className="overflow-hidden">
                            <p className="text-sm font-bold truncate text-cv-text">{user?.name || 'CodeVault User'}</p>
                            <p className="text-[10px] uppercase tracking-wider font-semibold text-cv-text-muted">
                                {userPlan} Plan
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-3 px-4 py-3 w-full rounded-xl border border-transparent text-cv-text-muted hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20 group transition-all duration-150 ease-in-out"
                    >
                        <LogOut size={18} className="group-hover:text-red-400 transition-colors duration-150" />
                        <span className="font-medium tracking-wide">Disconnect</span>
                    </button>
                </div>
            </aside>

            <main id="main-content" className="flex-1 overflow-hidden relative z-10">
                <div className="h-full overflow-y-auto p-8 scroll-smooth">
                    <Outlet />
                </div>
            </main>

            <GlobalBuildStatus />
        </div >
    );
};

export default Layout;

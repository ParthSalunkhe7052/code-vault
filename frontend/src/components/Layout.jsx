import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { LogOut, Activity, Shield, Crown, Zap, Sparkles } from 'lucide-react';
import { auth } from '../services/api';
import { useSettings } from '../contexts/SettingsContext';
import backgroundMain from '../assets/background_main.png';
import iconDashboard from '../assets/icon_dashboard.png';
import iconProjects from '../assets/icon_projects.png';
import iconKeys from '../assets/icon_keys.png';
import iconWebhooks from '../assets/icon_webhooks.png';
import iconSettings from '../assets/icon_settings.png';
import watermarkLogo from '../assets/watermark_logo.png';
import GlobalBuildStatus from './GlobalBuildStatus';

const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { settings } = useSettings();
    const isDarkMatter = settings.theme === 'dark-matter';

    const [user, setUser] = useState(null);

    useEffect(() => {
        const loadUser = async () => {
            try {
                const userData = await auth.getUser();
                setUser(userData);
            } catch (error) {
                console.error('Failed to load user:', error);
            }
        };
        loadUser();

        const handleUserUpdate = () => loadUser();
        window.addEventListener('user-updated', handleUserUpdate);
        return () => window.removeEventListener('user-updated', handleUserUpdate);
    }, []);

    const isAdmin = user?.role === 'admin';
    const userPlan = user?.plan || 'free';
    const PlanIcon = userPlan === 'enterprise' ? Crown : userPlan === 'pro' ? Zap : Sparkles;
    const planColor = userPlan === 'enterprise' ? 'text-amber-400' : userPlan === 'pro' ? 'text-violet-400' : 'text-slate-400';
    const planBg = userPlan === 'enterprise' ? 'bg-amber-500/10 border-amber-500/20' : userPlan === 'pro' ? 'bg-violet-500/10 border-violet-500/20' : 'bg-slate-800 border-white/10';

    const handleLogout = async () => {
        await auth.logout();
        navigate('/login');
    };

    // Modified Nav Items: Pricing moved above Settings
    const navItems = [
        { path: '/', icon: iconDashboard, label: 'Dashboard', isImage: true },
        { path: '/projects', icon: iconProjects, label: 'Projects', isImage: true },
        { path: '/licenses', icon: iconKeys, label: 'Access Keys', isImage: true },
        { path: '/webhooks', icon: iconWebhooks, label: 'Webhooks', isImage: true },
        // Pricing manually added with an icon since we don't have an image asset for it
        { path: '/pricing', icon: Crown, label: 'Pricing', isImage: false },
        { path: '/settings', icon: iconSettings, label: 'Settings', isImage: true },
    ];

    const primaryActiveClass = isDarkMatter
        ? 'bg-[var(--cv-primary)]/10 text-[var(--cv-text)] border-[var(--cv-primary)]/20 shadow-[0_0_15px_-5px_var(--cv-primary-glow)]'
        : 'bg-primary/10 text-white border-primary/20 shadow-[0_0_15px_-5px_rgba(99,102,241,0.3)]';

    return (
        <div className="flex h-screen w-full text-slate-200 overflow-hidden font-sans selection:bg-primary/30 selection:text-primary-light" style={{ backgroundColor: 'var(--cv-bg)' }}>
            <div className="fixed inset-0 bg-black pointer-events-none z-0" />
            <img src={backgroundMain} alt="Background" className={`fixed inset-0 w-full h-full object-cover pointer-events-none mix-blend-screen z-0 ${isDarkMatter ? 'opacity-20' : 'opacity-40'}`} />
            <div className="fixed inset-0 bg-grid-pattern opacity-10 pointer-events-none z-0" />
            <img 
                src={watermarkLogo} 
                alt="" 
                className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] opacity-[0.03] pointer-events-none z-0 select-none grayscale"
            />
            <div className="fixed inset-0 pointer-events-none z-0" style={{ background: `linear-gradient(to bottom, transparent, var(--cv-bg) 80%, var(--cv-bg))` }} />

            <aside className="w-72 flex flex-col border-r backdrop-blur-xl relative z-20" style={{ borderColor: 'var(--cv-border)', backgroundColor: 'var(--cv-card)' }}>
                <div className="p-6 border-b" style={{ borderColor: 'var(--cv-border)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-lg animate-pulse-slow" style={{ background: `linear-gradient(135deg, var(--cv-primary), var(--cv-primary-hover))`, boxShadow: '0 4px 14px -3px var(--cv-primary-glow)' }}>
                            <Activity size={22} />
                        </div>
                        <div>
                            <h1 className="font-bold text-lg tracking-wider uppercase" style={{ color: 'var(--cv-text)' }}>CodeVault</h1>
                            <p className="text-[10px] font-mono tracking-widest" style={{ color: 'var(--cv-primary)' }}>SYSTEM V2.0</p>
                        </div>
                    </div>
                </div>

                <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                    <div className="px-4 py-2 text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--cv-text-muted)' }}>
                        Mission Control
                    </div>
                    {navItems.map((item) => {
                        const IconComponent = item.isImage ? null : item.icon;
                        return (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/'}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-4 py-3 rounded-xl relative overflow-hidden border ${isActive
                                    ? primaryActiveClass
                                    : 'border-transparent hover:bg-[var(--cv-border-subtle)] hover:border-[var(--cv-border)]'
                                }`
                            }
                            style={({ isActive }) => ({
                                color: isActive ? 'var(--cv-text)' : 'var(--cv-text-muted)',
                                transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)'
                            })}
                        >
                            {item.isImage ? (
                                <img
                                    src={item.icon}
                                    alt={item.label}
                                    className={`w-8 h-8 object-contain mix-blend-screen transition-opacity duration-150 ${location.pathname === item.path || (item.path === '/' && location.pathname === '/')
                                        ? ''
                                        : 'opacity-70 hover:opacity-100'
                                        }`}
                                />
                            ) : (
                                <div className="w-8 h-8 flex items-center justify-center">
                                     <IconComponent size={20} />
                                </div>
                            )}
                            <span className="font-medium tracking-wide">{item.label}</span>
                            {(location.pathname === item.path || (item.path === '/' && location.pathname === '/')) && (
                                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-l-full" style={{ backgroundColor: 'var(--cv-primary)', boxShadow: '0 0 6px var(--cv-primary-glow)' }} />
                            )}
                        </NavLink>
                    )})}

                    {isAdmin && (
                        <>
                            <div className="mt-6 px-4 py-2 text-[10px] font-bold text-amber-500/70 uppercase tracking-widest">
                                Admin
                            </div>
                            <NavLink
                                to="/admin"
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-4 py-3 rounded-xl relative overflow-hidden border ${isActive
                                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-[0_0_8px_-3px_rgba(245,158,11,0.3)]'
                                        : 'border-transparent text-slate-400 hover:bg-[var(--cv-border-subtle)] hover:border-[var(--cv-border)]'
                                    }`
                                }
                            >
                                <div className="w-8 h-8 flex items-center justify-center">
                                    <Shield size={24} className="text-amber-400" />
                                </div>
                                <span className="font-medium tracking-wide">Admin Dashboard</span>
                                {location.pathname === '/admin' && (
                                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-amber-500 rounded-l-full shadow-[0_0_6px_rgba(245,158,11,0.6)]" />
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
                            `flex items-center gap-3 px-4 py-3 rounded-xl relative overflow-hidden border ${isActive
                                ? 'bg-purple-500/10 text-purple-400 border-purple-500/20 shadow-[0_0_8px_-3px_rgba(168,85,247,0.3)]'
                                : 'border-transparent text-slate-400 hover:bg-[var(--cv-border-subtle)] hover:border-[var(--cv-border)]'
                            }`
                        }
                    >
                        <div className="w-8 h-8 flex items-center justify-center">
                            <Activity size={24} className="text-purple-400" />
                        </div>
                        <span className="font-medium tracking-wide">Build Settings</span>
                        {location.pathname === '/build-settings' && (
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-purple-500 rounded-l-full shadow-[0_0_6px_rgba(168,85,247,0.6)]" />
                        )}
                    </NavLink>

                    <div className="mt-8 px-4 py-2 text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--cv-text-muted)' }}>
                        System Status
                    </div>
                    <div className="px-4 py-3 rounded-xl border mx-2" style={{ backgroundColor: 'var(--cv-bg-elevated)', borderColor: 'var(--cv-border)' }}>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs" style={{ color: 'var(--cv-text-muted)' }}>Core Systems</span>
                            <span className="text-xs text-emerald-400 font-mono">ONLINE</span>
                        </div>
                        <div className="w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--cv-muted)' }}>
                            <div className="h-full w-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)] animate-pulse" />
                        </div>
                    </div>
                </nav>

                <div className="p-4 border-t" style={{ borderColor: 'var(--cv-border)', backgroundColor: 'var(--cv-bg-secondary)' }}>
                    <div className="mb-4 flex items-center gap-3 px-2">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${planBg}`}>
                            <PlanIcon size={20} className={planColor} />
                        </div>
                        <div className="overflow-hidden">
                            <p className="text-sm font-bold truncate" style={{ color: 'var(--cv-text)' }}>{user?.name || 'CodeVault User'}</p>
                            <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: 'var(--cv-text-muted)' }}>
                                {userPlan} Plan
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-3 px-4 py-3 w-full rounded-xl border border-transparent text-slate-400 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20 group"
                        style={{ transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)' }}
                    >
                        <LogOut size={18} className="group-hover:text-red-400 transition-colors duration-150" />
                        <span className="font-medium tracking-wide">Disconnect</span>
                    </button>
                </div>
            </aside>

            <main className="flex-1 overflow-hidden relative z-10">
                <div className="h-full overflow-y-auto p-8 scroll-smooth">
                    <Outlet />
                </div>
            </main>

            <GlobalBuildStatus />
        </div >
    );
};

export default Layout;

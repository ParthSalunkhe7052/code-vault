import React from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { LogOut, Activity, Shield, Crown, Zap, Sparkles } from 'lucide-react';
import { auth } from '../services/api';
import backgroundMain from '../assets/background_main.png';
import iconDashboard from '../assets/icon_dashboard.png';
import iconProjects from '../assets/icon_projects.png';
import iconKeys from '../assets/icon_keys.png';
import iconWebhooks from '../assets/icon_webhooks.png';
import iconSettings from '../assets/icon_settings.png';

const Layout = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const user = auth.getUser();
    const isAdmin = user?.role === 'admin';

    // Determine plan badge
    const userPlan = user?.plan || 'free';
    const PlanIcon = userPlan === 'enterprise' ? Crown : userPlan === 'pro' ? Zap : Sparkles;
    const planColor = userPlan === 'enterprise' ? 'text-amber-400' : userPlan === 'pro' ? 'text-violet-400' : 'text-slate-400';
    const planBg = userPlan === 'enterprise' ? 'bg-amber-500/10 border-amber-500/20' : userPlan === 'pro' ? 'bg-violet-500/10 border-violet-500/20' : 'bg-slate-800 border-white/10';

    const handleLogout = () => {
        auth.logout();
        navigate('/login');
    };

    const navItems = [
        { path: '/', icon: iconDashboard, label: 'Dashboard', isImage: true },
        { path: '/projects', icon: iconProjects, label: 'Projects', isImage: true },
        { path: '/licenses', icon: iconKeys, label: 'Access Keys', isImage: true },
        { path: '/webhooks', icon: iconWebhooks, label: 'Webhooks', isImage: true },
        { path: '/settings', icon: iconSettings, label: 'Settings', isImage: true },
    ];

    return (
        <div className="flex h-screen w-full bg-background text-slate-200 overflow-hidden font-sans selection:bg-primary/30 selection:text-primary-light">
            {/* Background Effects */}
            <div className="fixed inset-0 bg-black pointer-events-none" />
            <img src={backgroundMain} alt="Background" className="fixed inset-0 w-full h-full object-cover opacity-40 pointer-events-none mix-blend-screen" />
            <div className="fixed inset-0 bg-grid-pattern opacity-10 pointer-events-none" />
            <div className="fixed inset-0 bg-gradient-to-b from-transparent via-background/80 to-background pointer-events-none" />

            {/* Sidebar */}
            <aside className="w-72 flex flex-col border-r border-white/15 bg-gray-900/50 backdrop-blur-xl relative z-10">
                <div className="p-6 border-b border-white/15">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-primary/20 animate-pulse-slow">
                            <Activity size={22} />
                        </div>
                        <div>
                            <h1 className="font-bold text-lg tracking-wider text-white uppercase">CodeVault</h1>
                            <p className="text-[10px] text-primary font-mono tracking-widest">SYSTEM V2.0</p>
                        </div>
                    </div>
                </div>

                <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                    <div className="px-4 py-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                        Mission Control
                    </div>
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/'}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden border ${isActive
                                    ? 'bg-primary/10 text-white border-primary/20 shadow-[0_0_15px_-5px_rgba(99,102,241,0.3)]'
                                    : 'border-transparent text-slate-400 hover:bg-white/5 hover:text-white hover:border-white/5 hover:translate-x-1'
                                }`
                            }
                        >
                            <img
                                src={item.icon}
                                alt={item.label}
                                className={`w-8 h-8 object-contain mix-blend-screen ${location.pathname === item.path || (item.path === '/' && location.pathname === '/')
                                    ? ''
                                    : 'opacity-70 group-hover:opacity-100 transition-opacity'
                                    }`}
                            />
                            <span className="font-medium tracking-wide">{item.label}</span>
                            {(location.pathname === item.path || (item.path === '/' && location.pathname === '/')) && (
                                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-l-full shadow-[0_0_10px_rgba(99,102,241,0.8)]" />
                            )}
                        </NavLink>
                    ))}

                    {/* Admin Section - Only visible to admins */}
                    {isAdmin && (
                        <>
                            <div className="mt-6 px-4 py-2 text-[10px] font-bold text-amber-500/70 uppercase tracking-widest">
                                Admin
                            </div>
                            <NavLink
                                to="/admin"
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden border ${isActive
                                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-[0_0_15px_-5px_rgba(245,158,11,0.3)]'
                                        : 'border-transparent text-slate-400 hover:bg-amber-500/5 hover:text-amber-400 hover:border-amber-500/10 hover:translate-x-1'
                                    }`
                                }
                            >
                                <div className="w-8 h-8 flex items-center justify-center">
                                    <Shield size={24} className="text-amber-400" />
                                </div>
                                <span className="font-medium tracking-wide">Admin Dashboard</span>
                                {location.pathname === '/admin' && (
                                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-amber-500 rounded-l-full shadow-[0_0_10px_rgba(245,158,11,0.8)]" />
                                )}
                            </NavLink>
                        </>
                    )}

                    {/* Build Tools Section */}
                    <div className="mt-6 px-4 py-2 text-[10px] font-bold text-purple-500/70 uppercase tracking-widest">
                        Build Tools
                    </div>
                    <NavLink
                        to="/build-settings"
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden border ${isActive
                                ? 'bg-purple-500/10 text-purple-400 border-purple-500/20 shadow-[0_0_15px_-5px_rgba(168,85,247,0.3)]'
                                : 'border-transparent text-slate-400 hover:bg-purple-500/5 hover:text-purple-400 hover:border-purple-500/10 hover:translate-x-1'
                            }`
                        }
                    >
                        <div className="w-8 h-8 flex items-center justify-center">
                            <Activity size={24} className="text-purple-400" />
                        </div>
                        <span className="font-medium tracking-wide">Build Settings</span>
                        {location.pathname === '/build-settings' && (
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-purple-500 rounded-l-full shadow-[0_0_10px_rgba(168,85,247,0.8)]" />
                        )}
                    </NavLink>

                    {/* Subscription Section */}
                    <div className="mt-6 px-4 py-2 text-[10px] font-bold text-emerald-500/70 uppercase tracking-widest">
                        Subscription
                    </div>
                    <NavLink
                        to="/pricing"
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden border ${isActive
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_15px_-5px_rgba(16,185,129,0.3)]'
                                : 'border-transparent text-slate-400 hover:bg-emerald-500/5 hover:text-emerald-400 hover:border-emerald-500/10 hover:translate-x-1'
                            }`
                        }
                    >
                        <div className="w-8 h-8 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-400">
                                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                            </svg>
                        </div>
                        <span className="font-medium tracking-wide">Pricing</span>
                        {location.pathname === '/pricing' && (
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-emerald-500 rounded-l-full shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
                        )}
                    </NavLink>
                    <NavLink
                        to="/billing"
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative overflow-hidden border ${isActive
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_15px_-5px_rgba(16,185,129,0.3)]'
                                : 'border-transparent text-slate-400 hover:bg-emerald-500/5 hover:text-emerald-400 hover:border-emerald-500/10 hover:translate-x-1'
                            }`
                        }
                    >
                        <div className="w-8 h-8 flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-400">
                                <rect width="20" height="14" x="2" y="5" rx="2" />
                                <line x1="2" x2="22" y1="10" y2="10" />
                            </svg>
                        </div>
                        <span className="font-medium tracking-wide">Billing</span>
                        {location.pathname === '/billing' && (
                            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-emerald-500 rounded-l-full shadow-[0_0_10px_rgba(16,185,129,0.8)]" />
                        )}
                    </NavLink>

                    <div className="mt-8 px-4 py-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                        System Status
                    </div>
                    <div className="px-4 py-3 rounded-xl bg-gray-800/60 border border-white/10 mx-2">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-xs text-slate-400">Core Systems</span>
                            <span className="text-xs text-emerald-400 font-mono">ONLINE</span>
                        </div>
                        <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full w-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)] animate-pulse" />
                        </div>
                    </div>
                </nav>

                <div className="p-4 border-t border-white/15 bg-gray-900/30">
                    {/* User Info with Plan Badge */}
                    <div className="mb-4 flex items-center gap-3 px-2">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${planBg}`}>
                            <PlanIcon size={20} className={planColor} />
                        </div>
                        <div className="overflow-hidden">
                            <p className="text-sm font-bold text-white truncate">{user?.name || 'CodeVault User'}</p>
                            <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                                {userPlan} Plan
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-3 px-4 py-3 w-full rounded-xl border border-transparent text-slate-400 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20 hover:translate-x-1 transition-all duration-200 group"
                    >
                        <LogOut size={18} className="group-hover:text-red-400 transition-colors" />
                        <span className="font-medium tracking-wide">Disconnect</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-hidden relative z-0">
                <div className="h-full overflow-y-auto p-8 scroll-smooth">
                    <Outlet />
                </div>
            </main>
        </div >
    );
};

export default Layout;


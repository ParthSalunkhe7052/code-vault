import React, { memo, useCallback } from 'react';
import { Shield, Timer, Unlock, Sparkles, Users, Key, ArrowRight, Info, CheckCircle, AlertTriangle } from 'lucide-react';

/**
 * BrandingNotice - Shows upgrade prompt for free tier or success message for Pro
 */
const BrandingNotice = memo(({ isPro, canRemoveBranding }) => {
    if (isPro || canRemoveBranding) {
        return (
            <div className="bg-green-900/20 border border-green-600/30 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle className="w-5 h-5" />
                    <span className="font-medium">Pro Feature Active</span>
                </div>
                <p className="text-sm text-slate-400 mt-1">
                    Your compiled applications will NOT show CodeVault branding.
                </p>
            </div>
        );
    }

    return (
        <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-2 text-yellow-400">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-medium">Free Tier Branding</span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
                Your compiled applications will show a "Protected by CodeVault" splash screen on startup.
            </p>
            <a 
                href="/pricing" 
                className="inline-flex items-center gap-1 text-sm text-purple-400 hover:text-purple-300 mt-2"
            >
                Upgrade to Pro to remove branding
                <ArrowRight className="w-4 h-4" />
            </a>
        </div>
    );
});

BrandingNotice.displayName = 'BrandingNotice';

/**
 * Step4License - Redesigned for Mission Control
 * Uses Bento-style cards for selection
 */
const Step4License = memo(({
    // Protection mode: 'generic' | 'demo' | 'none'
    protectionMode = 'generic',
    setProtectionMode,
    // Demo mode settings
    demoMode = false,
    setDemoMode,
    demoDuration = 60,
    setDemoDuration,
    // Tier info for branding notice
    isPro = false,
    canRemoveBranding = false
}) => {
    // Handle protection mode change - memoized
    const handleModeChange = useCallback((mode) => {
        setProtectionMode(mode);
        if (mode === 'demo') {
            setDemoMode(true);
        } else {
            setDemoMode(false);
        }
    }, [setProtectionMode, setDemoMode]);

    // Memoized demo duration handler
    const handleDemoDurationChange = useCallback((value) => {
        setDemoDuration(Number(value));
    }, [setDemoDuration]);

    return (
        <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl mx-auto">
            <div className="text-left">
                <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">Licensing & Protection</h2>
                <p className="text-slate-400">
                    Choose how your application will be distributed and protected.
                </p>
            </div>

            {/* Branding Notice for Free/Pro tier */}
            <BrandingNotice isPro={isPro} canRemoveBranding={canRemoveBranding} />

            {/* Protection Mode Options - 3 Column Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* 1. Generic Build - Hero Card */}
                <div 
                    onClick={() => handleModeChange('generic')}
                    className={`
                        relative overflow-hidden rounded-2xl border-2 cursor-pointer transition-all duration-300 group
                        ${protectionMode === 'generic'
                            ? 'border-emerald-500 bg-emerald-500/10 scale-[1.02] shadow-xl shadow-emerald-500/10'
                            : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                        }
                    `}
                >
                     {protectionMode === 'generic' && (
                        <div className="absolute top-0 right-0 p-3">
                             <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center shadow-lg">
                                <CheckCircle size={14} className="text-white" />
                             </div>
                        </div>
                    )}
                    
                    <div className="p-6 h-full flex flex-col">
                        <div className={`
                            w-14 h-14 rounded-2xl flex items-center justify-center mb-6 transition-colors
                            ${protectionMode === 'generic' ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30' : 'bg-white/10 text-slate-400'}
                        `}>
                            <Key size={28} />
                        </div>

                        <h3 className="text-xl font-bold text-white mb-2">Standard License</h3>
                        <p className="text-sm text-slate-400 mb-6 flex-1">
                            Distribute one build. Customers activate it with their unique license key at runtime.
                        </p>

                        <div className="space-y-2">
                             <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                                <CheckCircle size={12} className="text-emerald-500" />
                                <span>Unlimited Users</span>
                             </div>
                             <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                                <CheckCircle size={12} className="text-emerald-500" />
                                <span>HWID Locking</span>
                             </div>
                             <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                                <CheckCircle size={12} className="text-emerald-500" />
                                <span>Offline Access</span>
                             </div>
                        </div>
                    </div>
                </div>

                {/* 2. Demo Mode */}
                <div 
                    onClick={() => handleModeChange('demo')}
                    className={`
                        relative overflow-hidden rounded-2xl border-2 cursor-pointer transition-all duration-300 group
                        ${protectionMode === 'demo'
                            ? 'border-amber-500 bg-amber-500/10 scale-[1.02] shadow-xl shadow-amber-500/10'
                            : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                        }
                    `}
                >
                    {protectionMode === 'demo' && (
                        <div className="absolute top-0 right-0 p-3">
                             <div className="w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center shadow-lg">
                                <CheckCircle size={14} className="text-white" />
                             </div>
                        </div>
                    )}

                    <div className="p-6 h-full flex flex-col">
                        <div className={`
                            w-14 h-14 rounded-2xl flex items-center justify-center mb-6 transition-colors
                            ${protectionMode === 'demo' ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30' : 'bg-white/10 text-slate-400'}
                        `}>
                            <Timer size={28} />
                        </div>

                        <h3 className="text-xl font-bold text-white mb-2">Time-Limited Trial</h3>
                        <p className="text-sm text-slate-400 mb-6 flex-1">
                            Users can run the app freely for a set duration, then must purchase a key to continue.
                        </p>

                        {protectionMode === 'demo' ? (
                             <div className="bg-amber-500/20 rounded-xl p-3 border border-amber-500/30 animate-in fade-in slide-in-from-bottom-2">
                                <label className="text-xs font-bold text-amber-200 uppercase tracking-wider mb-1 block">Trial Duration</label>
                                <select
                                    value={demoDuration}
                                    onClick={(e) => e.stopPropagation()}
                                    onChange={(e) => handleDemoDurationChange(e.target.value)}
                                    className="w-full bg-black/30 text-white text-sm rounded-lg px-2 py-2 border border-white/10 focus:outline-none focus:border-amber-500"
                                >
                                    <option value="30">30 Minutes</option>
                                    <option value="60">1 Hour</option>
                                    <option value="120">2 Hours</option>
                                    <option value="1440">1 Day</option>
                                    <option value="10080">7 Days</option>
                                    <option value="43200">30 Days</option>
                                </select>
                             </div>
                        ) : (
                            <div className="mt-auto pt-4 border-t border-white/5">
                                <span className="text-xs font-medium text-slate-500">Ideal for Shareware / Demos</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* 3. No Protection */}
                <div 
                    onClick={() => handleModeChange('none')}
                    className={`
                        relative overflow-hidden rounded-2xl border-2 cursor-pointer transition-all duration-300 group
                        ${protectionMode === 'none'
                            ? 'border-red-500 bg-red-500/10 scale-[1.02] shadow-xl shadow-red-500/10'
                            : 'border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10'
                        }
                    `}
                >
                     {protectionMode === 'none' && (
                        <div className="absolute top-0 right-0 p-3">
                             <div className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center shadow-lg">
                                <CheckCircle size={14} className="text-white" />
                             </div>
                        </div>
                    )}

                    <div className="p-6 h-full flex flex-col">
                        <div className={`
                            w-14 h-14 rounded-2xl flex items-center justify-center mb-6 transition-colors
                            ${protectionMode === 'none' ? 'bg-red-500 text-white shadow-lg shadow-red-500/30' : 'bg-white/10 text-slate-400'}
                        `}>
                            <Unlock size={28} />
                        </div>

                        <h3 className="text-xl font-bold text-white mb-2">Unprotected</h3>
                        <p className="text-sm text-slate-400 mb-6 flex-1">
                            No license key required. The executable can be run by anyone, anywhere.
                        </p>

                        <div className="mt-auto p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-2">
                            <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
                            <p className="text-xs text-red-200">
                                Warning: This removes all piracy protection. Only use for free tools.
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* How It Works - Educational Panel (Bottom) */}
             <div className="mt-8 bg-white/5 border border-white/10 rounded-2xl p-6">
                 <h4 className="font-bold text-white mb-4 flex items-center gap-2">
                    <Info size={18} className="text-indigo-400" />
                    Workflow Preview
                </h4>
                
                {protectionMode === 'generic' && (
                    <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm relative">
                         {/* Connecting Line (Desktop) */}
                        <div className="hidden md:block absolute top-1/2 left-10 right-10 h-0.5 bg-white/5 -z-0" />

                        <div className="relative z-10 bg-gray-900 px-4 py-2 rounded-xl border border-white/10 text-center w-full md:w-auto">
                            <span className="block text-xs text-slate-500 mb-1">Step 1</span>
                            <span className="text-emerald-400 font-bold">Build .exe</span>
                        </div>
                         <div className="hidden md:block text-slate-600"><ArrowRight size={16} /></div>
                        <div className="relative z-10 bg-gray-900 px-4 py-2 rounded-xl border border-white/10 text-center w-full md:w-auto">
                            <span className="block text-xs text-slate-500 mb-1">Step 2</span>
                            <span className="text-white font-bold">Generate Keys</span>
                        </div>
                         <div className="hidden md:block text-slate-600"><ArrowRight size={16} /></div>
                        <div className="relative z-10 bg-gray-900 px-4 py-2 rounded-xl border border-white/10 text-center w-full md:w-auto">
                            <span className="block text-xs text-slate-500 mb-1">Step 3</span>
                            <span className="text-white font-bold">Send to User</span>
                        </div>
                         <div className="hidden md:block text-slate-600"><ArrowRight size={16} /></div>
                        <div className="relative z-10 bg-gray-900 px-4 py-2 rounded-xl border border-white/10 text-center w-full md:w-auto">
                            <span className="block text-xs text-slate-500 mb-1">Step 4</span>
                            <span className="text-indigo-400 font-bold">Activation</span>
                        </div>
                    </div>
                )}

                 {protectionMode === 'demo' && (
                     <div className="flex items-center gap-4 text-sm text-slate-400">
                        <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">!</div>
                        <p>
                            Users will enjoy <span className="text-white font-bold">{demoDuration < 60 ? `${demoDuration} minutes` : `${demoDuration/60} hours`}</span> of full access. 
                            When the timer hits zero, the app locks instantly and requests a purchased license key.
                        </p>
                     </div>
                )}

                {protectionMode === 'none' && (
                     <div className="flex items-center gap-4 text-sm text-slate-400">
                        <div className="w-8 h-8 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center font-bold">!</div>
                        <p>
                            Your application will have <span className="text-white font-bold">zero restrictions</span>. 
                            It can be copied, shared, and run on unlimited devices without your permission.
                        </p>
                     </div>
                )}
            </div>
        </div>
    );
});

Step4License.displayName = 'Step4License';

export default Step4License;

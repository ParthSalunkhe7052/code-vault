import React from 'react';
import { Shield, Timer, Unlock, Sparkles, Users, Key, ArrowRight, Info } from 'lucide-react';

/**
 * Step4License - Protection Settings
 * REDESIGNED: Now focuses on Generic Build workflow
 * - Generic Build: Customers enter keys at runtime
 * - Demo Mode: Trial period before requiring key
 * - No Protection: Unprotected build
 */
const Step4License = ({
    // Protection mode: 'generic' | 'demo' | 'none'
    protectionMode = 'generic',
    setProtectionMode,
    // Demo mode settings
    demoMode = false,
    setDemoMode,
    demoDuration = 60,
    setDemoDuration
}) => {
    // Handle protection mode change
    const handleModeChange = (mode) => {
        setProtectionMode(mode);
        // If demo mode, also set demoMode flag
        if (mode === 'demo') {
            setDemoMode(true);
        } else {
            setDemoMode(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white mb-2">Protection Settings</h2>
                <p className="text-slate-400 text-sm">
                    Choose how your app will be protected with license validation
                </p>
            </div>

            {/* Protection Mode Options */}
            <div className="space-y-3">
                {/* Generic Build - Recommended */}
                <label className={`
                    block p-5 rounded-xl border-2 cursor-pointer transition-all
                    ${protectionMode === 'generic'
                        ? 'border-emerald-500 bg-emerald-500/10'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }
                `}>
                    <input
                        type="radio"
                        name="protectionMode"
                        value="generic"
                        checked={protectionMode === 'generic'}
                        onChange={() => handleModeChange('generic')}
                        className="hidden"
                    />
                    <div className="flex items-start gap-4">
                        <div className={`
                            w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0
                            ${protectionMode === 'generic' ? 'bg-emerald-500/30' : 'bg-white/10'}
                        `}>
                            <Sparkles size={24} className={protectionMode === 'generic' ? 'text-emerald-400' : 'text-slate-400'} />
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center gap-2">
                                <h3 className="font-semibold text-white">Generic Build</h3>
                                <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full font-medium">
                                    Recommended
                                </span>
                            </div>
                            <p className="text-sm text-slate-400 mt-1">
                                Build once, distribute to unlimited customers. Each customer enters their own license key when they run the app.
                            </p>
                            <div className="flex items-center gap-4 mt-3 text-xs text-emerald-400">
                                <span className="flex items-center gap-1">
                                    <Users size={14} />
                                    Unlimited distribution
                                </span>
                                <span className="flex items-center gap-1">
                                    <Key size={14} />
                                    Runtime key entry
                                </span>
                            </div>
                        </div>
                        <div className={`
                            w-5 h-5 rounded-full border-2 flex-shrink-0
                            ${protectionMode === 'generic'
                                ? 'border-emerald-500 bg-emerald-500'
                                : 'border-slate-500'
                            }
                        `}>
                            {protectionMode === 'generic' && (
                                <div className="w-full h-full flex items-center justify-center">
                                    <div className="w-2 h-2 rounded-full bg-white" />
                                </div>
                            )}
                        </div>
                    </div>
                </label>

                {/* Demo/Trial Mode */}
                <label className={`
                    block p-5 rounded-xl border-2 cursor-pointer transition-all
                    ${protectionMode === 'demo'
                        ? 'border-amber-500 bg-amber-500/10'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }
                `}>
                    <input
                        type="radio"
                        name="protectionMode"
                        value="demo"
                        checked={protectionMode === 'demo'}
                        onChange={() => handleModeChange('demo')}
                        className="hidden"
                    />
                    <div className="flex items-start gap-4">
                        <div className={`
                            w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0
                            ${protectionMode === 'demo' ? 'bg-amber-500/30' : 'bg-white/10'}
                        `}>
                            <Timer size={24} className={protectionMode === 'demo' ? 'text-amber-400' : 'text-slate-400'} />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-white">Demo / Trial Mode</h3>
                            <p className="text-sm text-slate-400 mt-1">
                                App works without a license for a limited time, then requires activation. Perfect for try-before-you-buy.
                            </p>
                        </div>
                        <div className={`
                            w-5 h-5 rounded-full border-2 flex-shrink-0
                            ${protectionMode === 'demo'
                                ? 'border-amber-500 bg-amber-500'
                                : 'border-slate-500'
                            }
                        `}>
                            {protectionMode === 'demo' && (
                                <div className="w-full h-full flex items-center justify-center">
                                    <div className="w-2 h-2 rounded-full bg-white" />
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Demo Duration Selector */}
                    {protectionMode === 'demo' && (
                        <div className="mt-4 pt-4 border-t border-amber-500/20">
                            <label className="text-sm text-slate-300 mb-2 block">Trial Duration:</label>
                            <select
                                value={demoDuration}
                                onChange={(e) => setDemoDuration(Number(e.target.value))}
                                className="w-full px-3 py-2 bg-black/30 border border-amber-500/30 rounded-lg text-white focus:outline-none focus:border-amber-500"
                            >
                                <option value="30">30 minutes</option>
                                <option value="60">1 hour</option>
                                <option value="120">2 hours</option>
                                <option value="240">4 hours</option>
                                <option value="1440">24 hours (1 day)</option>
                                <option value="4320">3 days</option>
                                <option value="10080">7 days</option>
                                <option value="20160">14 days</option>
                                <option value="43200">30 days</option>
                            </select>
                            <p className="text-xs text-amber-400/70 mt-2">
                                After trial expires, user will need to enter a license key to continue using the app.
                            </p>
                        </div>
                    )}
                </label>

                {/* No Protection */}
                <label className={`
                    block p-5 rounded-xl border-2 cursor-pointer transition-all
                    ${protectionMode === 'none'
                        ? 'border-red-500 bg-red-500/10'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }
                `}>
                    <input
                        type="radio"
                        name="protectionMode"
                        value="none"
                        checked={protectionMode === 'none'}
                        onChange={() => handleModeChange('none')}
                        className="hidden"
                    />
                    <div className="flex items-start gap-4">
                        <div className={`
                            w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0
                            ${protectionMode === 'none' ? 'bg-red-500/30' : 'bg-white/10'}
                        `}>
                            <Unlock size={24} className={protectionMode === 'none' ? 'text-red-400' : 'text-slate-400'} />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-white">No Protection</h3>
                            <p className="text-sm text-slate-400 mt-1">
                                Anyone can run the app without a license key. No validation required.
                            </p>
                            {protectionMode === 'none' && (
                                <p className="text-xs text-red-400 mt-2">
                                    ⚠️ Your app will have no license protection
                                </p>
                            )}
                        </div>
                        <div className={`
                            w-5 h-5 rounded-full border-2 flex-shrink-0
                            ${protectionMode === 'none'
                                ? 'border-red-500 bg-red-500'
                                : 'border-slate-500'
                            }
                        `}>
                            {protectionMode === 'none' && (
                                <div className="w-full h-full flex items-center justify-center">
                                    <div className="w-2 h-2 rounded-full bg-white" />
                                </div>
                            )}
                        </div>
                    </div>
                </label>
            </div>

            {/* How It Works - Educational Panel */}
            {protectionMode === 'generic' && (
                <div className="bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-4">
                        <Info size={18} className="text-emerald-400" />
                        <h4 className="font-semibold text-white">How Generic Build Works</h4>
                    </div>
                    <div className="space-y-3">
                        <div className="flex items-start gap-3">
                            <div className="w-6 h-6 rounded-full bg-emerald-500/30 flex items-center justify-center text-emerald-400 text-xs font-bold flex-shrink-0">1</div>
                            <p className="text-sm text-slate-300"><strong className="text-white">Build your app</strong> — Creates a protected .exe file</p>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="w-6 h-6 rounded-full bg-emerald-500/30 flex items-center justify-center text-emerald-400 text-xs font-bold flex-shrink-0">2</div>
                            <p className="text-sm text-slate-300"><strong className="text-white">Create license keys</strong> — Go to Licenses page → Generate keys for each customer</p>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="w-6 h-6 rounded-full bg-emerald-500/30 flex items-center justify-center text-emerald-400 text-xs font-bold flex-shrink-0">3</div>
                            <p className="text-sm text-slate-300"><strong className="text-white">Distribute</strong> — Send the .exe and license key to your customer</p>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="w-6 h-6 rounded-full bg-emerald-500/30 flex items-center justify-center text-emerald-400 text-xs font-bold flex-shrink-0">4</div>
                            <p className="text-sm text-slate-300"><strong className="text-white">Customer activates</strong> — They enter the key when running the app</p>
                        </div>
                    </div>
                    <div className="mt-4 pt-4 border-t border-emerald-500/20 text-xs text-slate-400">
                        💡 The key is saved locally after first use, so customers only need to enter it once.
                    </div>
                </div>
            )}

            {protectionMode === 'demo' && (
                <div className="bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-4">
                        <Info size={18} className="text-amber-400" />
                        <h4 className="font-semibold text-white">How Trial Mode Works</h4>
                    </div>
                    <div className="space-y-2 text-sm text-slate-300">
                        <p>• Customer runs the app → Trial timer starts</p>
                        <p>• App works fully during trial period</p>
                        <p>• After trial expires → License key prompt appears</p>
                        <p>• Customer enters key to unlock permanently</p>
                    </div>
                    <div className="mt-4 pt-4 border-t border-amber-500/20 text-xs text-slate-400">
                        💡 Great for "try before you buy" software distribution model.
                    </div>
                </div>
            )}
        </div>
    );
};

export default Step4License;

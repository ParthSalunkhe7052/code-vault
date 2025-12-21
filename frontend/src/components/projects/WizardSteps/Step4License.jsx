import React from 'react';
import { Key, Shield, Plus, Clock, Infinity, Timer } from 'lucide-react';

/**
 * Step4License - Select a license for the build
 * Optional step - user can proceed without a license
 * Includes demo mode configuration for trial periods
 */
const Step4License = ({
    licenses = [],
    selectedLicense,
    setSelectedLicense,
    // Demo mode props
    demoMode = false,
    setDemoMode,
    demoDuration = 60,
    setDemoDuration
}) => {
    const activeLicenses = licenses.filter(l => l.status === 'active');

    const formatDate = (dateStr) => {
        if (!dateStr) return 'Never';
        return new Date(dateStr).toLocaleDateString();
    };

    return (
        <div className="space-y-6">
            <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-white mb-2">License & Trial Mode</h2>
                <p className="text-slate-400 text-sm">
                    Embed license protection or configure a trial period
                </p>
            </div>

            {/* License Options */}
            <div className="space-y-3">
                {/* No License Option */}
                <label className={`
                    block p-4 rounded-xl border-2 cursor-pointer transition-all
                    ${!selectedLicense
                        ? 'border-indigo-500 bg-indigo-500/10'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }
                `}>
                    <input
                        type="radio"
                        name="license"
                        value=""
                        checked={!selectedLicense}
                        onChange={() => setSelectedLicense('')}
                        className="hidden"
                    />
                    <div className="flex items-center gap-4">
                        <div className={`
                            w-12 h-12 rounded-full flex items-center justify-center
                            ${!selectedLicense ? 'bg-indigo-500/30' : 'bg-white/10'}
                        `}>
                            <Shield size={24} className={!selectedLicense ? 'text-indigo-400' : 'text-slate-400'} />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-white">No License Required</h3>
                            <p className="text-sm text-slate-400">
                                Build without license validation - anyone can run the executable
                            </p>
                        </div>
                        <div className={`
                            w-5 h-5 rounded-full border-2 
                            ${!selectedLicense
                                ? 'border-indigo-500 bg-indigo-500'
                                : 'border-slate-500'
                            }
                        `}>
                            {!selectedLicense && (
                                <div className="w-full h-full flex items-center justify-center">
                                    <div className="w-2 h-2 rounded-full bg-white" />
                                </div>
                            )}
                        </div>
                    </div>
                </label>

                {/* Active Licenses */}
                {activeLicenses.map(license => (
                    <label
                        key={license.id}
                        className={`
                            block p-4 rounded-xl border-2 cursor-pointer transition-all
                            ${selectedLicense === license.license_key
                                ? 'border-emerald-500 bg-emerald-500/10'
                                : 'border-white/10 bg-white/5 hover:border-white/20'
                            }
                        `}
                    >
                        <input
                            type="radio"
                            name="license"
                            value={license.license_key}
                            checked={selectedLicense === license.license_key}
                            onChange={() => setSelectedLicense(license.license_key)}
                            className="hidden"
                        />
                        <div className="flex items-center gap-4">
                            <div className={`
                                w-12 h-12 rounded-full flex items-center justify-center
                                ${selectedLicense === license.license_key ? 'bg-emerald-500/30' : 'bg-white/10'}
                            `}>
                                <Key size={24} className={
                                    selectedLicense === license.license_key ? 'text-emerald-400' : 'text-slate-400'
                                } />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-semibold text-white font-mono text-sm">
                                    {license.license_key}
                                </h3>
                                <div className="flex items-center gap-4 mt-1 text-xs text-slate-400">
                                    {license.client_name && (
                                        <span>{license.client_name}</span>
                                    )}
                                    <span className="flex items-center gap-1">
                                        {license.expires_at ? (
                                            <>
                                                <Clock size={12} />
                                                Expires: {formatDate(license.expires_at)}
                                            </>
                                        ) : (
                                            <>
                                                <Infinity size={12} />
                                                Never expires
                                            </>
                                        )}
                                    </span>
                                </div>
                            </div>
                            <div className={`
                                w-5 h-5 rounded-full border-2 
                                ${selectedLicense === license.license_key
                                    ? 'border-emerald-500 bg-emerald-500'
                                    : 'border-slate-500'
                                }
                            `}>
                                {selectedLicense === license.license_key && (
                                    <div className="w-full h-full flex items-center justify-center">
                                        <div className="w-2 h-2 rounded-full bg-white" />
                                    </div>
                                )}
                            </div>
                        </div>
                    </label>
                ))}
            </div>

            {/* Create License Link */}
            {activeLicenses.length === 0 && (
                <div className="text-center p-6 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-slate-400 mb-4">No active licenses for this project</p>
                    <a
                        href="/licenses"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors"
                    >
                        <Plus size={18} />
                        Create a License
                    </a>
                </div>
            )}

            {/* Demo Mode Option */}
            <div className={`mt-6 p-4 rounded-xl border transition-all ${demoMode
                    ? 'bg-amber-500/10 border-amber-500/30'
                    : 'bg-white/5 border-white/10'
                }`}>
                <label className="flex items-center gap-4 cursor-pointer">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${demoMode ? 'bg-amber-500/30' : 'bg-white/10'
                        }`}>
                        <Timer size={20} className={demoMode ? 'text-amber-400' : 'text-slate-400'} />
                    </div>
                    <div className="flex-1">
                        <span className={`font-medium ${demoMode ? 'text-amber-400' : 'text-white'}`}>
                            Enable Demo/Trial Mode
                        </span>
                        <p className="text-xs text-slate-400 mt-1">
                            App works without license for a limited time, then requires activation
                        </p>
                    </div>
                    <div className={`w-12 h-6 rounded-full p-1 transition-colors ${demoMode ? 'bg-amber-500' : 'bg-slate-600'
                        }`}>
                        <div className={`w-4 h-4 rounded-full bg-white transition-transform ${demoMode ? 'translate-x-6' : 'translate-x-0'
                            }`} />
                    </div>
                    <input
                        type="checkbox"
                        checked={demoMode}
                        onChange={(e) => setDemoMode(e.target.checked)}
                        className="hidden"
                    />
                </label>

                {demoMode && (
                    <div className="mt-4 space-y-4 pt-4 border-t border-amber-500/20">
                        <div>
                            <label className="text-sm text-slate-300 mb-2 block">Demo Duration:</label>
                            <select
                                value={demoDuration}
                                onChange={(e) => setDemoDuration(Number(e.target.value))}
                                className="input w-full"
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
                        </div>

                        <div className="bg-slate-800/50 rounded-lg p-3 text-xs text-slate-400">
                            <p className="font-medium text-white mb-2 flex items-center gap-2">
                                <Timer size={14} />
                                How Demo Mode Works:
                            </p>
                            <ul className="list-disc list-inside space-y-1">
                                <li>App runs normally for the demo period</li>
                                <li>Timer starts on first launch after build</li>
                                <li>After expiry, app shows license prompt</li>
                                <li>User can enter a valid license to unlock</li>
                            </ul>
                            {selectedLicense && (
                                <p className="mt-2 text-amber-400">
                                    💡 Once demo expires, the app will validate against license: <code>{selectedLicense}</code>
                                </p>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Info Box */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                <p className="text-sm text-blue-400">
                    💡 <strong>How license protection works:</strong>
                </p>
                <p className="text-xs text-slate-400 mt-2">
                    When a license is selected, the compiled executable will validate the license
                    with your server before running. Users without a valid license won't be able
                    to use the software.
                </p>
            </div>
        </div>
    );
};

export default Step4License;

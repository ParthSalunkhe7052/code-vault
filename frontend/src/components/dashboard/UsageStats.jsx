
import { Link } from 'react-router-dom';
import { BarChart, Lock } from 'lucide-react';
import { usePricing, TIERS } from '../../contexts/PricingContext';

const UsageBar = ({ label, current, max, color = "bg-violet-500" }) => {
    const isUnlimited = max === Infinity;
    const percentage = isUnlimited ? 0 : Math.min((current / max) * 100, 100);
    
    return (
        <div className="mb-4">
            <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300">{label}</span>
                <span className="text-white font-medium">
                    {current} / {isUnlimited ? '∞' : max}
                </span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div 
                    className={`h-full ${color} transition-all duration-500`}
                    style={{ width: `${isUnlimited ? 100 : percentage}%` }}
                />
            </div>
        </div>
    );
};

const UsageStats = ({ projectCount = 0, licenseCount = 0 }) => {
    const { getLimits, tier } = usePricing();
    const limits = getLimits();

    return (
        <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-violet-500/20">
                        <BarChart size={20} className="text-violet-400" />
                    </div>
                    <h3 className="font-bold text-white">Plan Usage</h3>
                </div>
                <div className="px-2 py-1 rounded bg-slate-700 text-xs font-mono text-slate-300 uppercase">
                    {tier}
                </div>
            </div>

            <UsageBar 
                label="Projects" 
                current={projectCount} 
                max={limits.maxProjects} 
                color={projectCount >= limits.maxProjects && limits.maxProjects !== Infinity ? "bg-red-500" : "bg-violet-500"}
            />
            
            <UsageBar 
                label="Active Licenses" 
                current={licenseCount} 
                max={limits.maxLicenses}
                color={licenseCount >= limits.maxLicenses && limits.maxLicenses !== Infinity ? "bg-red-500" : "bg-emerald-500"}
            />

            <div className="mt-6 pt-4 border-t border-slate-700/50">
                {tier === TIERS.FREE ? (
                    <Link to="/pricing" className="flex items-center justify-center gap-2 w-full py-2 bg-gradient-to-r from-violet-600 to-indigo-600 rounded-lg text-white font-medium hover:from-violet-500 hover:to-indigo-500 transition-all">
                        <Lock size={16} />
                        Upgrade to Pro
                    </Link>
                ) : (
                    <p className="text-center text-xs text-slate-500">
                        Thank you for supporting CodeVault!
                    </p>
                )}
            </div>
        </div>
    );
};

export default UsageStats;

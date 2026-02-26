import { Database, Key, Activity, TrendingUp, CheckCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

const QuickStatsBar = ({ projectCount, licenseStats, validationStats }) => {
    const successRate = validationStats?.last_24h?.total > 0
        ? Math.round((validationStats.last_24h.successful / validationStats.last_24h.total) * 100)
        : null;

    const activeLicenses = licenseStats?.active || 0;
    const totalLicenses = licenseStats?.total || 0;

    return (
        <div className="glass-card p-4 mb-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-wrap items-center gap-6">
                    <Link to="/projects" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                            <Database size={18} className="text-blue-400" />
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Projects</p>
                            <p className="text-lg font-bold text-white">{projectCount}</p>
                        </div>
                    </Link>

                    <div className="w-px h-10 bg-white/10 hidden sm:block" />

                    <Link to="/licenses" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <div className="p-2 rounded-lg bg-violet-500/10 border border-violet-500/20">
                            <Key size={18} className="text-violet-400" />
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Licenses</p>
                            <p className="text-lg font-bold text-white">
                                {activeLicenses}
                                {totalLicenses > activeLicenses && (
                                    <span className="text-sm font-normal text-slate-400 ml-1">/ {totalLicenses}</span>
                                )}
                            </p>
                        </div>
                    </Link>

                    <div className="w-px h-10 bg-white/10 hidden sm:block" />

                    <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                            {successRate !== null ? (
                                <TrendingUp size={18} className="text-emerald-400" />
                            ) : (
                                <Activity size={18} className="text-emerald-400" />
                            )}
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wide">Validations (24h)</p>
                            <p className="text-lg font-bold text-white">
                                {validationStats?.last_24h?.total || 0}
                                {successRate !== null && (
                                    <span className={`text-sm font-normal ml-2 ${successRate >= 90 ? 'text-emerald-400' : successRate >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                                        {successRate}% success
                                    </span>
                                )}
                            </p>
                        </div>
                    </div>
                </div>

                {activeLicenses > 0 && (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                        <CheckCircle size={14} className="text-emerald-400" />
                        <span className="text-xs font-medium text-emerald-400">System Active</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default QuickStatsBar;

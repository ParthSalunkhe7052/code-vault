import { Calendar } from 'lucide-react';

const ExpiringLicense = ({ license }) => {
    const daysUntil = Math.ceil((new Date(license.expires_at) - new Date()) / (1000 * 60 * 60 * 24));

    return (
        <div className="flex items-center gap-4 py-3 border-b border-white/5 last:border-0">
            <div className={`p-2 rounded-lg ${daysUntil <= 3 ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}`}>
                <Calendar size={16} />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-white truncate">
                        {license.license_key}
                    </span>
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                    {license.client_name || 'No client'} • {license.project_name}
                </div>
            </div>
            <span className={`text-sm font-medium ${daysUntil <= 3 ? 'text-red-400' : 'text-amber-400'}`}>
                {daysUntil}d left
            </span>
        </div>
    );
};

export default ExpiringLicense;

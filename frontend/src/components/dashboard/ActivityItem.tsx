import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, Globe } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';

interface ActivityItemProps {
    activity: {
        result: string;
        license_key: string;
        client_name?: string;
        ip_address?: string;
        created_at: string | number | Date;
    };
}

const ActivityItem: React.FC<ActivityItemProps> = ({ activity }) => {
    const getResultIcon = (result: string) => {
        switch (result) {
            case 'valid':
                return <CheckCircle size={14} className="text-emerald-400" />;
            case 'invalid':
            case 'revoked':
            case 'expired':
                return <XCircle size={14} className="text-red-400" />;
            default:
                return <AlertTriangle size={14} className="text-amber-400" />;
        }
    };

    const getResultColor = (result: string) => {
        switch (result) {
            case 'valid':
                return 'text-emerald-400';
            case 'invalid':
            case 'revoked':
            case 'expired':
                return 'text-red-400';
            default:
                return 'text-amber-400';
        }
    };

    return (
        <div className="flex items-center gap-4 py-3 border-b border-white/5 last:border-0">
            <div className="p-2 rounded-lg bg-white/5">
                {getResultIcon(activity.result)}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-indigo-300 truncate">
                        {activity.license_key}
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${getResultColor(activity.result)} bg-white/5`}>
                        {activity.result}
                    </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                    {activity.client_name && <span>{activity.client_name}</span>}
                    {activity.ip_address && (
                        <span className="flex items-center gap-1">
                            <Globe size={10} />
                            {activity.ip_address}
                        </span>
                    )}
                </div>
            </div>
            <span className="text-xs text-slate-500 whitespace-nowrap">
                {formatRelativeTime(activity.created_at)}
            </span>
        </div>
    );
};

export default ActivityItem;

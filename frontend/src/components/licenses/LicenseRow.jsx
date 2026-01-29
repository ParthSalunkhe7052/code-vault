import React from 'react';
import { Copy, Key, Calendar, Folder, Monitor, Ban, Trash2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const getStatusBadge = (status) => {
    switch (status) {
        case 'active':
            return (
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle size={12} /> Active
                </span>
            );
        case 'revoked':
            return (
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                    <XCircle size={12} /> Revoked
                </span>
            );
        default:
            return (
                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <AlertTriangle size={12} /> {status}
                </span>
            );
    }
};

const LicenseRow = ({
    license,
    isSelected,
    onSelect,
    onViewBindings,
    onRevoke,
    onDelete,
    getProjectName,
    copyToClipboard,
    animationDelay
}) => {
    return (
        <tr
            className="group hover:bg-white/5 transition-colors animate-fade-in"
            style={{ animationDelay: `${animationDelay}ms` }}
        >
            <td>
                <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onSelect(license.id)}
                    className="rounded border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500"
                />
            </td>
            <td className="font-mono text-sm">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded bg-white/5 text-slate-400">
                        <Key size={14} />
                    </div>
                    <span className="text-indigo-300 font-medium">{license.license_key}</span>
                    <button
                        onClick={() => copyToClipboard(license.license_key)}
                        className="text-slate-500 hover:text-white opacity-0 group-hover:opacity-100 transition-all"
                        title="Copy Key"
                    >
                        <Copy size={14} />
                    </button>
                </div>
            </td>
            <td>
                <div className="flex items-center gap-2">
                    <Folder size={14} className="text-blue-400" />
                    <span className="text-sm text-slate-300">{getProjectName(license.project_id)}</span>
                </div>
            </td>
            <td>
                <div className="flex flex-col">
                    <span className="font-medium text-white">{license.client_name || 'Unknown Client'}</span>
                    <span className="text-xs text-slate-500">{license.client_email || 'No email'}</span>
                </div>
            </td>
            <td>
                {getStatusBadge(license.status)}
            </td>
            <td>
                {license.expires_at ? (
                    <ExpirationDate expiresAt={license.expires_at} />
                ) : (
                    <span className="text-slate-500 text-sm">Never</span>
                )}
            </td>
            <td>
                <div className="flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-indigo-500 rounded-full"
                            style={{ width: `${(license.active_machines / license.max_machines) * 100}%` }}
                        />
                    </div>
                    <span className="text-xs text-slate-400">
                        {license.active_machines}/{license.max_machines}
                    </span>
                </div>
            </td>
            <td>
                <div className="flex flex-wrap gap-1 max-w-[150px]">
                    {(license.features || []).slice(0, 2).map((feature, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs bg-indigo-500/20 text-indigo-300 rounded-full">
                            {feature}
                        </span>
                    ))}
                    {(license.features || []).length > 2 && (
                        <span className="px-2 py-0.5 text-xs bg-slate-500/20 text-slate-400 rounded-full">
                            +{license.features.length - 2}
                        </span>
                    )}
                </div>
            </td>
            <td>
                <div className="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                    <button
                        onClick={() => onViewBindings(license)}
                        className="p-2 rounded-lg hover:bg-indigo-500/20 text-slate-400 hover:text-indigo-400 transition-colors"
                        title="View Machines"
                    >
                        <Monitor size={16} />
                    </button>
                    {license.status === 'active' && (
                        <button
                            onClick={() => onRevoke(license.id)}
                            className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                            title="Revoke License"
                        >
                            <Ban size={16} />
                        </button>
                    )}
                    <button
                        onClick={() => onDelete(license.id)}
                        className="p-2 rounded-lg hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
                        title="Delete License"
                    >
                        <Trash2 size={16} />
                    </button>
                </div>
            </td>
        </tr>
    );
};

const ExpirationDate = ({ expiresAt }) => {
    const daysUntilExpiry = Math.ceil((new Date(expiresAt) - new Date()) / (1000 * 60 * 60 * 24));
    
    let colorClass = 'text-slate-400';
    if (daysUntilExpiry < 0) colorClass = 'text-red-400';
    else if (daysUntilExpiry < 7) colorClass = 'text-red-400';
    else if (daysUntilExpiry < 30) colorClass = 'text-amber-400';
    
    return (
        <div className="flex items-center gap-2">
            <Calendar size={14} className={colorClass} />
            <span className={colorClass}>
                {new Date(expiresAt).toLocaleDateString()}
            </span>
        </div>
    );
};

export default LicenseRow;

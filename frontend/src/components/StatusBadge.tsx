import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, Clock, Pause, Ban, Zap, LucideIcon } from 'lucide-react';

/**
 * Reusable status badge component
 * Provides consistent styling for status indicators across the app
 */

interface StatusInfo {
    icon: LucideIcon;
    className: string;
    label: string;
}

const statusConfig: Record<string, StatusInfo> = {
    active: {
        icon: CheckCircle,
        className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        label: 'Active'
    },
    revoked: {
        icon: XCircle,
        className: 'bg-red-500/10 text-red-400 border-red-500/20',
        label: 'Revoked'
    },
    expired: {
        icon: AlertTriangle,
        className: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        label: 'Expired'
    },
    pending: {
        icon: Clock,
        className: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        label: 'Pending'
    },
    paused: {
        icon: Pause,
        className: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
        label: 'Paused'
    },
    inactive: {
        icon: Ban,
        className: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
        label: 'Inactive'
    },
    running: {
        icon: Zap,
        className: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
        label: 'Running'
    },
    completed: {
        icon: CheckCircle,
        className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        label: 'Completed'
    },
    failed: {
        icon: XCircle,
        className: 'bg-red-500/10 text-red-400 border-red-500/20',
        label: 'Failed'
    },
    success: {
        icon: CheckCircle,
        className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        label: 'Success'
    },
    warning: {
        icon: AlertTriangle,
        className: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        label: 'Warning'
    },
    error: {
        icon: XCircle,
        className: 'bg-red-500/10 text-red-400 border-red-500/20',
        label: 'Error'
    }
};

/**
 * StatusBadge Component
 */
interface StatusBadgeProps {
    status?: string;
    customLabel?: string;
    size?: 'sm' | 'md' | 'lg';
    showIcon?: boolean;
    className?: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
    status,
    customLabel,
    size = 'md',
    showIcon = true,
    className = ''
}) => {
    const config = (status && statusConfig[status.toLowerCase()]) || {
        icon: AlertTriangle,
        className: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
        label: status || 'Unknown'
    };

    const Icon = config.icon;

    const sizeClasses = {
        sm: 'px-2 py-0.5 text-xs gap-1',
        md: 'px-2.5 py-1 text-xs gap-1.5',
        lg: 'px-3 py-1.5 text-sm gap-2'
    };

    const iconSizes = {
        sm: 10,
        md: 12,
        lg: 14
    };

    return (
        <span
            className={`
                inline-flex items-center rounded-full font-medium border
                ${sizeClasses[size]}
                ${config.className}
                ${className}
            `}
        >
            {showIcon && <Icon size={iconSizes[size]} />}
            {customLabel || config.label}
        </span>
    );
};

/**
 * Get status config for custom implementations
 */
export const getStatusConfig = (status?: string): StatusInfo => {
    const config = status ? statusConfig[status.toLowerCase()] : undefined;
    return config || statusConfig['inactive']!;
};

export default StatusBadge;

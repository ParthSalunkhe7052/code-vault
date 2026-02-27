/**
 * Date and number formatting utilities
 */

/**
 * Format a date string to a readable format
 */
export const formatDate = (dateString: string | Date | null | undefined, options: Intl.DateTimeFormatOptions = {}): string => {
    if (!dateString) return 'N/A';

    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid Date';

        const defaultOptions: Intl.DateTimeFormatOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            ...options
        };

        return date.toLocaleDateString(undefined, defaultOptions);
    } catch {
        return 'Invalid Date';
    }
};

/**
 * Format a date string to include time
 */
export const formatDateTime = (dateString: string | Date | null | undefined): string => {
    if (!dateString) return 'N/A';

    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid Date';

        return date.toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return 'Invalid Date';
    }
};

/**
 * Format a date as relative time (e.g., "In 5 days", "2 days ago")
 */
export const formatRelativeTime = (dateString: string | Date | null | undefined): string => {
    if (!dateString) return 'N/A';

    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid Date';

        const now = new Date();
        const diffMs = date.getTime() - now.getTime();
        const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays < -30) return formatDate(dateString);
        if (diffDays < -7) return `${Math.abs(Math.ceil(diffDays / 7))} weeks ago`;
        if (diffDays < -1) return `${Math.abs(diffDays)} days ago`;
        if (diffDays === -1) return 'Yesterday';
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Tomorrow';
        if (diffDays < 7) return `In ${diffDays} days`;
        if (diffDays < 30) return `In ${Math.ceil(diffDays / 7)} weeks`;

        return formatDate(dateString);
    } catch {
        return 'Invalid Date';
    }
};

/**
 * Get the number of days until a date expires
 */
export const getDaysUntilExpiry = (dateString: string | Date | null | undefined): number | null => {
    if (!dateString) return null;

    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return null;

        const now = new Date();
        return Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    } catch {
        return null;
    }
};

/**
 * Get the CSS color class based on days until expiry
 */
export const getExpiryColorClass = (daysUntilExpiry: number | null): string => {
    if (daysUntilExpiry === null) return 'text-slate-400';
    if (daysUntilExpiry < 0) return 'text-red-400';
    if (daysUntilExpiry < 7) return 'text-red-400';
    if (daysUntilExpiry < 30) return 'text-amber-400';
    return 'text-slate-400';
};

/**
 * Format a number with thousands separators
 */
export const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString();
};

/**
 * Format bytes to human readable format
 */
export const formatBytes = (bytes: number, decimals = 2): string => {
    if (bytes === 0) return '0 Bytes';
    if (!bytes) return 'N/A';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Format a duration in milliseconds to human readable format
 */
export const formatDuration = (ms: number | null | undefined): string => {
    if (!ms) return '0s';

    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    }
    if (minutes > 0) {
        return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
};

/**
 * Truncate a string with ellipsis
 */
export const truncate = (str: string | null | undefined, maxLength = 50): string => {
    if (!str) return '';
    if (str.length <= maxLength) return str;
    return str.slice(0, maxLength - 3) + '...';
};

/**
 * Format a license key for display (show first and last 4 chars)
 */
export const maskLicenseKey = (key: string | null | undefined): string => {
    if (!key || key.length < 12) return key || '';
    return `${key.slice(0, 4)}...${key.slice(-4)}`;
};

/**
 * Logger utility
 * Only outputs in development mode
 * Can be extended to send errors to a reporting service in production
 */

const isDev = import.meta.env.DEV;

const logger = {
    /**
     * Log informational messages (development only)
     */
    log: (...args) => {
        if (isDev) {
            console.log('[CodeVault]', ...args);
        }
    },

    /**
     * Log error messages
     * In production, this could be extended to send to error reporting service
     */
    error: (...args) => {
        if (isDev) {
            console.error('[CodeVault Error]', ...args);
        }
        // In production, you could send to error reporting service:
        // e.g., Sentry.captureException(args[0]);
    },

    /**
     * Log warning messages (development only)
     */
    warn: (...args) => {
        if (isDev) {
            console.warn('[CodeVault Warning]', ...args);
        }
    },

    /**
     * Log debug messages (development only)
     */
    debug: (...args) => {
        if (isDev) {
            console.debug('[CodeVault Debug]', ...args);
        }
    },

    /**
     * Log with a specific category/tag
     */
    tagged: (tag, ...args) => {
        if (isDev) {
            console.log(`[CodeVault:${tag}]`, ...args);
        }
    },

    /**
     * Log a table (development only)
     */
    table: (data, columns) => {
        if (isDev) {
            console.table(data, columns);
        }
    },

    /**
     * Start a timer (development only)
     */
    time: (label) => {
        if (isDev) {
            console.time(`[CodeVault] ${label}`);
        }
    },

    /**
     * End a timer (development only)
     */
    timeEnd: (label) => {
        if (isDev) {
            console.timeEnd(`[CodeVault] ${label}`);
        }
    },

    /**
     * Create a group (development only)
     */
    group: (label) => {
        if (isDev) {
            console.group(`[CodeVault] ${label}`);
        }
    },

    /**
     * End a group (development only)
     */
    groupEnd: () => {
        if (isDev) {
            console.groupEnd();
        }
    }
};

export default logger;

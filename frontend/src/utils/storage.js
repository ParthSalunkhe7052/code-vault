/**
 * Safe localStorage wrapper
 * Handles errors gracefully for:
 * - Private browsing mode (storage disabled)
 * - Quota exceeded errors
 * - JSON parse errors
 */

const safeStorage = {
    /**
     * Get a JSON value from localStorage
     * @param {string} key - Storage key
     * @param {*} defaultValue - Default value if key doesn't exist or error occurs
     * @returns {*} Parsed value or default
     */
    get: (key, defaultValue = null) => {
        try {
            const item = localStorage.getItem(key);
            if (item === null) return defaultValue;
            return JSON.parse(item);
        } catch (error) {
            console.warn(`[Storage] Failed to get "${key}":`, error.message);
            return defaultValue;
        }
    },

    /**
     * Set a JSON value in localStorage
     * @param {string} key - Storage key
     * @param {*} value - Value to store (will be JSON stringified)
     * @returns {boolean} True if successful
     */
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.warn(`[Storage] Failed to set "${key}":`, error.message);
            // Check if it's a quota exceeded error
            if (error.name === 'QuotaExceededError' || error.code === 22) {
                console.warn('[Storage] Storage quota exceeded. Consider clearing old data.');
            }
            return false;
        }
    },

    /**
     * Remove a key from localStorage
     * @param {string} key - Storage key
     * @returns {boolean} True if successful
     */
    remove: (key) => {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.warn(`[Storage] Failed to remove "${key}":`, error.message);
            return false;
        }
    },

    /**
     * Get a raw string value from localStorage (no JSON parsing)
     * @param {string} key - Storage key
     * @param {string} defaultValue - Default value if key doesn't exist
     * @returns {string} String value or default
     */
    getString: (key, defaultValue = null) => {
        try {
            const value = localStorage.getItem(key);
            return value !== null ? value : defaultValue;
        } catch (error) {
            console.warn(`[Storage] Failed to get string "${key}":`, error.message);
            return defaultValue;
        }
    },

    /**
     * Set a raw string value in localStorage (no JSON stringification)
     * @param {string} key - Storage key
     * @param {string} value - String value to store
     * @returns {boolean} True if successful
     */
    setString: (key, value) => {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (error) {
            console.warn(`[Storage] Failed to set string "${key}":`, error.message);
            return false;
        }
    },

    /**
     * Check if localStorage is available
     * @returns {boolean} True if localStorage is available
     */
    isAvailable: () => {
        try {
            const testKey = '__storage_test__';
            localStorage.setItem(testKey, testKey);
            localStorage.removeItem(testKey);
            return true;
        } catch (error) {
            return false;
        }
    },

    /**
     * Clear all localStorage data
     * @returns {boolean} True if successful
     */
    clear: () => {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.warn('[Storage] Failed to clear storage:', error.message);
            return false;
        }
    }
};

export default safeStorage;

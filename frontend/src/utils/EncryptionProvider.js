/**
 * EncryptionProvider - Secure localStorage wrapper using Web Crypto API
 * 
 * Provides encryption/decryption for sensitive data stored in localStorage.
 * Uses AES-GCM encryption with a derived key from a password.
 * 
 * @example
 * import { secureLocalStorage } from './utils/EncryptionProvider';
 * await secureLocalStorage.setItem('token', 'my-secret-token');
 * const token = await secureLocalStorage.getItem('token');
 */

// Generate a stable encryption key from the app identifier
// In production, this could be derived from user credentials
const APP_KEY_SALT = 'codevault-encryption-salt-v1';
const APP_IDENTIFIER = 'license-wrapper-secure-storage';

/**
 * Derives an AES-GCM key from the app identifier using PBKDF2
 * @returns {Promise<CryptoKey>} The derived encryption key
 */
async function deriveKey() {
    const encoder = new TextEncoder();

    // Import the app identifier as key material
    const keyMaterial = await crypto.subtle.importKey(
        'raw',
        encoder.encode(APP_IDENTIFIER),
        'PBKDF2',
        false,
        ['deriveKey']
    );

    // Derive the actual AES-GCM key
    return crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: encoder.encode(APP_KEY_SALT),
            iterations: 100000,
            hash: 'SHA-256'
        },
        keyMaterial,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );
}

/**
 * Encrypts data using AES-GCM
 * @param {string} data - The data to encrypt
 * @returns {Promise<string>} Base64 encoded encrypted data with IV
 */
export async function encrypt(data) {
    if (!data) return null;

    try {
        const key = await deriveKey();
        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(data);

        // Generate a random IV for each encryption
        const iv = crypto.getRandomValues(new Uint8Array(12));

        const encryptedBuffer = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv },
            key,
            dataBuffer
        );

        // Combine IV + encrypted data and encode as base64
        const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
        combined.set(iv);
        combined.set(new Uint8Array(encryptedBuffer), iv.length);

        return btoa(String.fromCharCode(...combined));
    } catch (error) {
        console.error('Encryption failed:', error);
        throw new Error('Failed to encrypt data');
    }
}

/**
 * Decrypts data encrypted with the encrypt function
 * @param {string} encryptedData - Base64 encoded encrypted data with IV
 * @returns {Promise<string>} The decrypted data
 */
export async function decrypt(encryptedData) {
    if (!encryptedData) return null;

    try {
        const key = await deriveKey();

        // Decode base64 and extract IV + encrypted data
        const combined = Uint8Array.from(atob(encryptedData), c => c.charCodeAt(0));
        const iv = combined.slice(0, 12);
        const data = combined.slice(12);

        const decryptedBuffer = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv },
            key,
            data
        );

        const decoder = new TextDecoder();
        return decoder.decode(decryptedBuffer);
    } catch (error) {
        console.error('Decryption failed:', error);
        // Return null for corrupted or invalid data
        return null;
    }
}

/**
 * Secure localStorage wrapper that automatically encrypts/decrypts values
 * 
 * @example
 * import { secureLocalStorage } from './utils/EncryptionProvider';
 * 
 * // Store encrypted data
 * await secureLocalStorage.setItem('auth_token', 'secret-jwt-token');
 * 
 * // Retrieve decrypted data
 * const token = await secureLocalStorage.getItem('auth_token');
 * 
 * // Remove data
 * secureLocalStorage.removeItem('auth_token');
 */
export const secureLocalStorage = {
    /**
     * Store an encrypted value in localStorage
     * @param {string} key - Storage key
     * @param {*} value - Value to store (will be JSON stringified if object)
     * @returns {Promise<void>}
     */
    async setItem(key, value) {
        const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
        const encryptedValue = await encrypt(stringValue);
        localStorage.setItem(`secure_${key}`, encryptedValue);
    },

    /**
     * Retrieve and decrypt a value from localStorage
     * @param {string} key - Storage key
     * @param {boolean} parseJson - Whether to parse the result as JSON (default: false)
     * @returns {Promise<*>} The decrypted value or null
     */
    async getItem(key, parseJson = false) {
        const encryptedValue = localStorage.getItem(`secure_${key}`);
        if (!encryptedValue) return null;

        const decryptedValue = await decrypt(encryptedValue);
        if (!decryptedValue) return null;

        if (parseJson) {
            try {
                return JSON.parse(decryptedValue);
            } catch {
                return decryptedValue;
            }
        }
        return decryptedValue;
    },

    /**
     * Remove an item from localStorage
     * @param {string} key - Storage key
     */
    removeItem(key) {
        localStorage.removeItem(`secure_${key}`);
    },

    /**
     * Clear all secure items from localStorage
     */
    clear() {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key?.startsWith('secure_')) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach(key => localStorage.removeItem(key));
    }
};

/**
 * Sensitive keys that should use secureLocalStorage
 * This list helps identify which keys contain sensitive data
 */
export const SENSITIVE_KEYS = [
    'license_wrapper_token',
    'license_wrapper_user',
    'auth_token',
    'api_key',
    'codevault_settings'
];

/**
 * Check if a key is sensitive and should be encrypted
 * @param {string} key - The localStorage key to check
 * @returns {boolean} True if the key should be encrypted
 */
export function isSensitiveKey(key) {
    return SENSITIVE_KEYS.some(sensitiveKey =>
        key.toLowerCase().includes(sensitiveKey.toLowerCase()) ||
        key.toLowerCase().includes('token') ||
        key.toLowerCase().includes('password') ||
        key.toLowerCase().includes('secret') ||
        key.toLowerCase().includes('key')
    );
}

export default {
    encrypt,
    decrypt,
    secureLocalStorage,
    SENSITIVE_KEYS,
    isSensitiveKey
};

/**
 * EncryptionProvider - Secure localStorage wrapper using Web Crypto API
 *
 * Provides encryption/decryption for sensitive data stored in localStorage.
 * Uses AES-GCM-256 encryption with a key derived per storage item from a
 * caller-supplied secret (e.g. JWT token or a server-issued per-session nonce).
 *
 * IMPORTANT: The encryption key MUST vary per user and per session. Never pass
 * a hardcoded constant string as the secret — that provides no security.
 *
 * @example
 * import { secureLocalStorage } from './utils/EncryptionProvider';
 * // secret is typically the user's current JWT token
 * await secureLocalStorage.setItem('user_profile', data, jwtToken);
 * const profile = await secureLocalStorage.getItem('user_profile', jwtToken);
 */

const PBKDF2_ITERATIONS = 100_000;
const PBKDF2_HASH = 'SHA-256';

/**
 * Derives an AES-GCM-256 key from a caller-supplied secret and a per-item salt.
 *
 * Using the storage key name as additional PBKDF2 salt domain-separates items so
 * that even if two items happen to use the same secret they get different keys.
 *
 * @param {string} secret   - Per-session secret (e.g. JWT token). Must NOT be a
 *                            hardcoded constant.
 * @param {string} itemKey  - The localStorage item name, used as domain separator.
 * @returns {Promise<CryptoKey>}
 */
async function deriveKey(secret, itemKey) {
    if (!secret || typeof secret !== 'string' || secret.length < 8) {
        throw new Error(
            '[EncryptionProvider] A per-user, per-session secret is required to derive ' +
            'the encryption key. Do not pass an empty string or a hardcoded constant.'
        );
    }

    const encoder = new TextEncoder();

    const keyMaterial = await crypto.subtle.importKey(
        'raw',
        encoder.encode(secret),
        'PBKDF2',
        false,
        ['deriveKey']
    );

    // Domain-separate items: salt = SHA-256(itemKey) so each stored item gets its own key
    const saltBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(`cv-item:${itemKey}`));

    return crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt: saltBuffer,
            iterations: PBKDF2_ITERATIONS,
            hash: PBKDF2_HASH,
        },
        keyMaterial,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );
}

/**
 * Encrypts data using AES-GCM-256 with a per-session, per-item derived key.
 *
 * @param {string} data     - Plaintext to encrypt.
 * @param {string} secret   - Per-session secret (e.g. JWT token).
 * @param {string} itemKey  - The storage key name (used as domain separator).
 * @returns {Promise<string>} Base64-encoded IV + ciphertext blob.
 */
export async function encrypt(data, secret, itemKey) {
    if (!data) return null;

    try {
        const key = await deriveKey(secret, itemKey);
        const encoder = new TextEncoder();
        const iv = crypto.getRandomValues(new Uint8Array(12));

        const encryptedBuffer = await crypto.subtle.encrypt(
            { name: 'AES-GCM', iv },
            key,
            encoder.encode(data)
        );

        const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
        combined.set(iv);
        combined.set(new Uint8Array(encryptedBuffer), iv.length);

        return btoa(String.fromCharCode(...combined));
    } catch (error) {
        console.error('[EncryptionProvider] Encryption failed:', error);
        throw new Error('Failed to encrypt data');
    }
}

/**
 * Decrypts data encrypted with encrypt().
 *
 * @param {string} encryptedData - Base64-encoded IV + ciphertext blob.
 * @param {string} secret        - Per-session secret used during encryption.
 * @param {string} itemKey       - The storage key name (used as domain separator).
 * @returns {Promise<string|null>} Decrypted plaintext, or null if decryption fails.
 */
export async function decrypt(encryptedData, secret, itemKey) {
    if (!encryptedData) return null;

    try {
        const key = await deriveKey(secret, itemKey);
        const combined = Uint8Array.from(atob(encryptedData), c => c.charCodeAt(0));
        const iv = combined.slice(0, 12);
        const ciphertext = combined.slice(12);

        const decryptedBuffer = await crypto.subtle.decrypt(
            { name: 'AES-GCM', iv },
            key,
            ciphertext
        );

        return new TextDecoder().decode(decryptedBuffer);
    } catch {
        // Return null for corrupted, tampered, or wrong-key data — do not throw.
        return null;
    }
}

/**
 * Secure localStorage wrapper.
 *
 * Every read and write requires the caller to supply the current session secret
 * (typically the JWT token). Items encrypted with a previous secret cannot be
 * decrypted after logout/token rotation — they are effectively invalidated.
 *
 * @example
 * import { secureLocalStorage } from './utils/EncryptionProvider';
 *
 * // Store (secret = current JWT)
 * await secureLocalStorage.setItem('user_profile', profileObj, jwtToken);
 *
 * // Retrieve
 * const profile = await secureLocalStorage.getItem('user_profile', jwtToken, true);
 *
 * // Remove
 * secureLocalStorage.removeItem('user_profile');
 */
export const secureLocalStorage = {
    /**
     * Encrypt and store a value.
     *
     * @param {string} key     - Storage key.
     * @param {*}      value   - Value to store (objects are JSON-serialised).
     * @param {string} secret  - Per-session secret (e.g. JWT token).
     */
    async setItem(key, value, secret) {
        const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
        const encryptedValue = await encrypt(stringValue, secret, key);
        localStorage.setItem(`secure_${key}`, encryptedValue);
    },

    /**
     * Retrieve and decrypt a value.
     *
     * Returns null when the item does not exist or the secret is wrong (e.g.
     * after a logout / token rotation — the old ciphertext is unreadable).
     *
     * @param {string}  key        - Storage key.
     * @param {string}  secret     - Per-session secret used when storing.
     * @param {boolean} parseJson  - Parse result as JSON (default: false).
     * @returns {Promise<*>}
     */
    async getItem(key, secret, parseJson = false) {
        const encryptedValue = localStorage.getItem(`secure_${key}`);
        if (!encryptedValue) return null;

        const decryptedValue = await decrypt(encryptedValue, secret, key);
        if (!decryptedValue) return null;

        if (parseJson) {
            try { return JSON.parse(decryptedValue); } catch { return decryptedValue; }
        }
        return decryptedValue;
    },

    /** Remove a single item. */
    removeItem(key) {
        localStorage.removeItem(`secure_${key}`);
    },

    /** Clear all items written by this wrapper. */
    clear() {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            if (k?.startsWith('secure_')) keysToRemove.push(k);
        }
        keysToRemove.forEach(k => localStorage.removeItem(k));
    },
};

/**
 * Sensitive storage keys that must use secureLocalStorage (not plain localStorage).
 */
export const SENSITIVE_KEYS = [
    'license_wrapper_token',
    'license_wrapper_user',
    'auth_token',
    'api_key',
];

/**
 * Returns true if a key name indicates sensitive data.
 * @param {string} key
 * @returns {boolean}
 */
export function isSensitiveKey(key) {
    return SENSITIVE_KEYS.some(s =>
        key.toLowerCase().includes(s.toLowerCase()) ||
        key.toLowerCase().includes('token') ||
        key.toLowerCase().includes('password') ||
        key.toLowerCase().includes('secret') ||
        key.toLowerCase().includes('key')
    );
}

export default { encrypt, decrypt, secureLocalStorage, SENSITIVE_KEYS, isSensitiveKey };

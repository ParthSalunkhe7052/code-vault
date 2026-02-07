export const secureLocalStorage: {
    setItem(key: string, value: any): Promise<void>;
    getItem(key: string, parseJson?: boolean): Promise<any>;
    removeItem(key: string): Promise<void>;
    clear(): void;
};
export function encrypt(data: string): Promise<string>;
export function decrypt(encryptedData: string): Promise<string | null>;
export const SENSITIVE_KEYS: string[];
export function isSensitiveKey(key: string): boolean;
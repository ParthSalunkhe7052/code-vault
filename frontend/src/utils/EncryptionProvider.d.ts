export const secureLocalStorage: {
    setItem(key: string, value: any, secret: string): Promise<void>;
    getItem(key: string, secret: string, parseJson?: boolean): Promise<any>;
    removeItem(key: string): Promise<void>;
    clear(): void;
};
export function encrypt(data: string, secret: string, itemKey: string): Promise<string>;
export function decrypt(encryptedData: string, secret: string, itemKey: string): Promise<string | null>;
export const SENSITIVE_KEYS: string[];
export function isSensitiveKey(key: string): boolean;

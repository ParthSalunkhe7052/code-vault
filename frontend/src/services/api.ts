import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { secureLocalStorage } from '../utils/EncryptionProvider';
import {
    User, AuthResponse,
    Project, CreateProjectRequest, ProjectConfig,
    License, CreateLicenseRequest, HardwareBinding,
    Webhook, CreateWebhookRequest, UpdateWebhookRequest, WebhookDelivery, WebhookEvent,
    BuildJob, DashboardStats,
    AdminStats, AdminUser, SubscriptionStatus,
} from '../types/api';

/**
 * Sanitizes a filename to prevent path traversal and other security issues
 * @param {string} filename - The filename to sanitize
 * @returns {string} - Safe filename
 */
function sanitizeFilename(filename: string): string {
    if (!filename) return 'download';

    // Remove any path components (../, ./, /)
    const parts = filename.split(/[\\/]/);
    let safeName = parts[parts.length - 1];

    if (!safeName) return 'download';

    // Remove any remaining dangerous characters
    safeName = safeName.replace(/[^a-zA-Z0-9._-]/g, '_');

    // Ensure filename isn't too long
    if (safeName.length > 100) {
        const ext = safeName.split('.').pop();
        safeName = safeName.substring(0, 95) + (ext ? '.' + ext : '');
    }

    // Prevent empty or hidden files
    if (!safeName || safeName.startsWith('.')) {
        safeName = 'download';
    }

    return safeName;
}

const TOKEN_KEY = 'license_wrapper_token';
const USER_KEY = 'license_wrapper_user';

// In-memory cache for token (to avoid async overhead on every request)
// Populated on app initialization and after login
let cachedToken: string | null = null;

// Detect if running in Tauri desktop app
const isTauri = typeof window !== 'undefined' && (window as any).__TAURI__ !== undefined;

// In Tauri or Production Web, we need the full URL
// In local dev mode, use relative path (Vite proxy handles it)
const API_BASE_URL = (isTauri || import.meta.env.PROD)
    ? `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`
    : '/api/v1';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Fixed stable app-instance secret stored in sessionStorage (not localStorage).
// Generated fresh on each browser session and never persisted across tabs.
// This is NOT a substitute for a proper per-user key, but it prevents
// offline extraction of tokens from localStorage by attackers who only have
// disk access (not an active session).
function _getSessionSecret(): string {
    const SESSION_SECRET_KEY = '__cv_ss';
    let secret = sessionStorage.getItem(SESSION_SECRET_KEY);
    if (!secret) {
        // Generate a cryptographically random 32-byte hex string per browser session
        const bytes = new Uint8Array(32);
        crypto.getRandomValues(bytes);
        secret = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
        sessionStorage.setItem(SESSION_SECRET_KEY, secret);
    }
    return secret;
}

/**
 * Initialize auth from encrypted storage.
 * Call this on app startup to populate the token cache.
 */
export async function initializeAuth(): Promise<string | null> {
    try {
        const secret = _getSessionSecret();
        cachedToken = await secureLocalStorage.getItem(TOKEN_KEY, secret);
    } catch (error) {
        console.error('Failed to initialize auth:', error);
        cachedToken = null;
    }
    return cachedToken;
}

// Add a request interceptor to include the JWT token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    if (cachedToken) {
        config.headers['Authorization'] = `Bearer ${cachedToken}`;
    }
    // Remove Content-Type for FormData - let browser set it with boundary
    if (config.data instanceof FormData) {
        delete config.headers['Content-Type'];
    }
    return config;
});

// Add response interceptor for handling auth errors
api.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Clear cached token and encrypted storage
            cachedToken = null;
            try {
                secureLocalStorage.removeItem(TOKEN_KEY);
                secureLocalStorage.removeItem(USER_KEY);
            } catch (cleanupError) {
                console.error('Failed to clean up auth storage:', cleanupError);
            }
            // Dispatch session-expired event instead of hard navigation
            // This allows React components to handle it gracefully (show modal, preserve state)
            window.dispatchEvent(new Event('session-expired'));
        }
        return Promise.reject(error);
    }
);

export const auth = {
    login: async (email: string, password: string): Promise<User> => {
        const response = await api.post<AuthResponse>('/auth/login', { email, password });
        const { access_token, user } = response.data;
        // Store encrypted token and user data using per-session key
        const secret = _getSessionSecret();
        await secureLocalStorage.setItem(TOKEN_KEY, access_token, secret);
        await secureLocalStorage.setItem(USER_KEY, user, secret);
        // Update cached token for immediate use
        cachedToken = access_token;
        return user;
    },
    register: async (email: string, password: string, name: string): Promise<User> => {
        const response = await api.post<AuthResponse>('/auth/register', { email, password, name });
        const { access_token, user } = response.data;
        // Store encrypted token and user data using per-session key
        const secret = _getSessionSecret();
        await secureLocalStorage.setItem(TOKEN_KEY, access_token, secret);
        await secureLocalStorage.setItem(USER_KEY, user, secret);
        // Update cached token for immediate use
        cachedToken = access_token;
        return user;
    },
    logout: async (): Promise<void> => {
        cachedToken = null;
        secureLocalStorage.removeItem(TOKEN_KEY);
        secureLocalStorage.removeItem(USER_KEY);
    },
    isAuthenticated: (): boolean => {
        return !!cachedToken;
    },
    getUser: async (): Promise<User | null> => {
        const secret = _getSessionSecret();
        const user = await secureLocalStorage.getItem(USER_KEY, secret, true);
        return user || null;
    },
    getMe: (): Promise<User> => api.get<User>('/auth/me').then(res => res.data),
    refreshUser: async (): Promise<User> => {
        const response = await api.get<User>('/auth/me');
        const user = response.data;
        const secret = _getSessionSecret();
        await secureLocalStorage.setItem(USER_KEY, user, secret);
        return user;
    },
    regenerateApiKey: (): Promise<{ api_key: string }> => api.post('/auth/regenerate-api-key').then(res => res.data),
    // Helper to get the current token (for downloads, etc.)
    getToken: (): string | null => cachedToken,
};

export const projects = {
    list: (): Promise<Project[]> => api.get('/projects').then(res => res.data),
    create: (data: CreateProjectRequest): Promise<Project> => api.post('/projects', data).then(res => res.data),
    delete: (id: string): Promise<{ success: boolean }> => api.delete(`/projects/${id}`).then(res => res.data),
    getConfig: (id: string): Promise<ProjectConfig> => api.get(`/projects/${id}/config`).then(res => res.data),
    updateConfig: (id: string, data: Partial<ProjectConfig>): Promise<ProjectConfig> => api.put(`/projects/${id}/config`, data).then(res => res.data),
    uploadFiles: (id: string, files: File[], onProgress?: (progress: number) => void): Promise<{ message: string; files: string[] }> => {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i] as Blob);
        }
        // Don't set Content-Type header - let browser set it with boundary
        return api.post(`/projects/${id}/upload`, formData, {
            onUploadProgress: (progressEvent) => {
                if (onProgress && progressEvent.total) {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(progress);
                }
            },
            timeout: 300000, // 5 minutes for large files
        }).then(res => res.data);
    },
    uploadZip: (id: string, file: File, onProgress?: (progress: number) => void): Promise<{ message: string; files: string[] }> => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post(`/projects/${id}/upload-zip`, formData, {
            onUploadProgress: (progressEvent) => {
                if (onProgress && progressEvent.total) {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    onProgress(progress);
                }
            },
            timeout: 300000, // 5 minutes for large files
        }).then(res => res.data);
    },
    listFiles: (id: string): Promise<any[]> => api.get(`/projects/${id}/files`).then(res => res.data),
    deleteFile: (projectId: string, fileId: string): Promise<{ success: boolean }> => api.delete(`/projects/${projectId}/files/${fileId}`).then(res => res.data),
};

export const compile = {
    start: (projectId: string, data: any = {}): Promise<{ job_id: string; status: string }> => api.post(`/compile/start?project_id=${projectId}`, data).then(res => res.data),
    getStatus: (jobId: string): Promise<BuildJob> => api.get(`/compile/${jobId}/status`).then(res => res.data),
    listJobs: (projectId: string): Promise<BuildJob[]> => api.get('/compile/jobs', { params: { project_id: projectId } }).then(res => res.data),
    download: async (jobId: string, filename: string): Promise<void> => {
        const token = auth.getToken();
        // Use proper URL based on environment (Tauri vs browser)
        const baseUrl = isTauri ? (import.meta.env.VITE_API_URL || 'http://localhost:8000') : '';
        const response = await fetch(`${baseUrl}/api/v1/compile/${jobId}/download`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) throw new Error('Download failed');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // SECURITY: Sanitize filename to prevent path traversal
        a.download = sanitizeFilename(filename || 'download');
        // Prevent the anchor from being visible or interactive
        a.style.display = 'none';
        a.setAttribute('tabindex', '-1');
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    },
};

export const licenses = {
    list: (projectId: string): Promise<License[]> => api.get('/licenses', { params: { project_id: projectId } }).then(res => res.data),
    create: (data: CreateLicenseRequest): Promise<License> => api.post('/licenses', data).then(res => res.data),
    revoke: (id: string): Promise<License> => api.post(`/licenses/${id}/revoke`).then(res => res.data),
    delete: (id: string): Promise<{ success: boolean }> => api.delete(`/licenses/${id}`).then(res => res.data),
    getBindings: (id: string): Promise<HardwareBinding[]> => api.get(`/licenses/${id}/bindings`).then(res => res.data),
    removeBinding: (licenseId: string, bindingId: string): Promise<{ success: boolean }> => api.delete(`/licenses/${licenseId}/bindings/${bindingId}`).then(res => res.data),
    // HWID Reset
    resetHwid: (id: string, reason: string): Promise<{ success: boolean }> => api.post(`/licenses/${id}/reset-hwid`, { reason }).then(res => res.data),
    getResetHistory: (id: string): Promise<any[]> => api.get(`/licenses/${id}/reset-history`).then(res => res.data),
    getResetStatus: (id: string): Promise<any> => api.get(`/licenses/${id}/reset-status`).then(res => res.data),
};

export const webhooks = {
    list: (): Promise<Webhook[]> => api.get('/webhooks').then(res => res.data),
    create: (data: CreateWebhookRequest): Promise<Webhook> => api.post('/webhooks', data).then(res => res.data),
    get: (id: string): Promise<Webhook> => api.get(`/webhooks/${id}`).then(res => res.data),
    update: (id: string, data: UpdateWebhookRequest): Promise<Webhook> => api.put(`/webhooks/${id}`, data).then(res => res.data),
    delete: (id: string): Promise<{ success: boolean }> => api.delete(`/webhooks/${id}`).then(res => res.data),
    getDeliveries: (id: string, limit: number = 50): Promise<WebhookDelivery[]> => api.get(`/webhooks/${id}/deliveries`, { params: { limit } }).then(res => res.data),
    test: (id: string): Promise<{ success: boolean; status_code: number; response_body: string }> => api.post(`/webhooks/${id}/test`).then(res => res.data),
    getEvents: (): Promise<WebhookEvent[]> => api.get('/webhooks/events/list').then(res => res.data),
};

export const stats = {
    getDashboard: (): Promise<DashboardStats> => api.get('/stats/dashboard').then(res => res.data),
    // License Analytics
    getLicenseAnalytics: (projectId?: string, days: number = 30): Promise<any> => 
        api.get('/analytics/licenses', { params: { project_id: projectId, days } }).then(res => res.data),
};

// Admin API (admin role required)
export const admin = {
    getStats: (): Promise<AdminStats> => api.get('/admin/stats').then(res => res.data),
    getUsers: (): Promise<AdminUser[]> => api.get('/admin/users').then(res => res.data),
    getAnalytics: (days: number = 30): Promise<any> => api.get('/admin/analytics', { params: { days } }).then(res => res.data),
    // New endpoints
    getRevenue: (): Promise<any> => api.get('/admin/revenue').then(res => res.data),
    getSystemHealth: (): Promise<any> => api.get('/admin/system-health').then(res => res.data),
    updateUserPlan: (userId: string, plan: string): Promise<User> => api.put(`/admin/users/${userId}/plan`, { plan }).then(res => res.data),
    updateUserRole: (userId: string, role: string): Promise<User> => api.put(`/admin/users/${userId}/role`, { role }).then(res => res.data),
    banUser: (userId: string): Promise<{ success: boolean }> => api.post(`/admin/users/${userId}/ban`).then(res => res.data),
};

// Polar/Subscription API
export const subscription = {
    getStatus: (): Promise<SubscriptionStatus> => api.get('/subscription/status').then(res => res.data),
    createCheckout: (productId: string): Promise<{ checkout_url: string }> =>
        api.post('/polar/create-checkout', { product_id: productId }).then(res => res.data),
};

// Public Store API (no auth required) - uses different base URL
const publicApi = axios.create({
    baseURL: isTauri ? `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1` : '/api/v1',
    headers: { 'Content-Type': 'application/json' },
});

// Cloud Build API
export const cloudBuild = {
    // Start a cloud build
    start: (projectId: string, data: any = {}): Promise<{ job_id: string; status: string }> => 
        api.post('/cloud-build/start', { project_id: projectId, ...data }).then(res => res.data),
    
    // Get build status with stage progress (sync=true syncs with GCP for running builds)
    getStatus: (buildId: string, sync: boolean = false): Promise<any> => 
        api.get(`/cloud-build/${buildId}/status`, { params: sync ? { sync: true } : {} }).then(res => res.data),
    
    // Direct GCP sync - bypasses webhook issues
    gcpSync: (buildId: string): Promise<any> => 
        api.get(`/cloud-build/${buildId}/gcp-sync`).then(res => res.data),
    
    // Cancel a running build
    cancel: (buildId: string): Promise<{ success: boolean }> => 
        api.post(`/cloud-build/${buildId}/cancel`).then(res => res.data),
    
    // Retry a failed build
    retry: (buildId: string): Promise<{ job_id: string; status: string }> => 
        api.post(`/cloud-build/${buildId}/retry`).then(res => res.data),
    
    // Cleanup build artifacts
    cleanup: (buildId: string): Promise<{ success: boolean }> => 
        api.post(`/cloud-build/${buildId}/cleanup`).then(res => res.data),
    
    // Get build history
    getHistory: (limit: number = 20, offset: number = 0): Promise<any> => 
        api.get('/cloud-build/history', { params: { limit, offset } }).then(res => res.data),
    
    // Get artifacts for a build (deprecated - use getStatus instead)
    getArtifacts: (buildId: string): Promise<any[]> => 
        api.get(`/cloud-build/${buildId}/status`).then(res => res.data.artifacts),
};

export const publicStore = {
    getProject: (storeSlug: string): Promise<any> => publicApi.get(`/public/store/${storeSlug}`).then(res => res.data),
    purchaseLicense: (storeSlug: string, buyerEmail: string, buyerName: string, successUrl: string, cancelUrl: string): Promise<any> =>
        publicApi.post('/public/purchase', {
            store_slug: storeSlug,
            buyer_email: buyerEmail,
            buyer_name: buyerName,
            success_url: successUrl,
            cancel_url: cancelUrl
        }).then(res => res.data),
    getLicensePortal: (licenseKey: string): Promise<any> => publicApi.get(`/public/license/${licenseKey}`).then(res => res.data),
};

// Demo Build API (time-limited trial binaries — unlimited for all tiers)
export const trialBuilds = {
    validate: (projectId: string, demoDurationMinutes: number = 60): Promise<{
        allowed: boolean;
        trial_builds_remaining: number;
        trial_builds_limit: number;
        trial_token?: string;
        tier: string;
    }> => api.post('/builds/trial/validate', { project_id: projectId, demo_duration_minutes: demoDurationMinutes }).then(res => res.data),
    
    record: (trialToken: string): Promise<{ status: string; trial_build_id: string }> => 
        api.post(`/builds/trial/record?trial_token=${trialToken}`).then(res => res.data),
    
    getStatus: (): Promise<{
        tier: string;
        trial_builds_limit: number;
        trial_builds_remaining: number;
        unlimited: boolean;
    }> => api.get('/builds/trial/status').then(res => res.data),
};

export default api;

import axios from 'axios';
import { secureLocalStorage } from '../utils/EncryptionProvider';

/**
 * Sanitizes a filename to prevent path traversal and other security issues
 * @param {string} filename - The filename to sanitize
 * @returns {string} - Safe filename
 */
function sanitizeFilename(filename) {
    if (!filename) return 'download';

    // Remove any path components (../, ./, /)
    const parts = filename.split(/[\\/]/);
    let safeName = parts[parts.length - 1];

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
let cachedToken = null;

// Detect if running in Tauri desktop app
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

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

/**
 * Initialize auth from encrypted storage.
 * Call this on app startup to populate the token cache.
 */
export async function initializeAuth() {
    try {
        cachedToken = await secureLocalStorage.getItem(TOKEN_KEY);
    } catch (error) {
        console.error('Failed to initialize auth:', error);
        cachedToken = null;
    }
    return cachedToken;
}

// Add a request interceptor to include the JWT token
api.interceptors.request.use((config) => {
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
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Clear cached token and encrypted storage
            cachedToken = null;
            await secureLocalStorage.removeItem(TOKEN_KEY);
            await secureLocalStorage.removeItem(USER_KEY);
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export const auth = {
    login: async (email, password) => {
        const response = await api.post('/auth/login', { email, password });
        const { access_token, user } = response.data;
        // Store encrypted token and user data
        await secureLocalStorage.setItem(TOKEN_KEY, access_token);
        await secureLocalStorage.setItem(USER_KEY, user);
        // Update cached token for immediate use
        cachedToken = access_token;
        return user;
    },
    register: async (email, password, name) => {
        const response = await api.post('/auth/register', { email, password, name });
        const { access_token, user } = response.data;
        // Store encrypted token and user data
        await secureLocalStorage.setItem(TOKEN_KEY, access_token);
        await secureLocalStorage.setItem(USER_KEY, user);
        // Update cached token for immediate use
        cachedToken = access_token;
        return user;
    },
    logout: async () => {
        cachedToken = null;
        await secureLocalStorage.removeItem(TOKEN_KEY);
        await secureLocalStorage.removeItem(USER_KEY);
    },
    isAuthenticated: () => {
        return !!cachedToken;
    },
    getUser: async () => {
        const user = await secureLocalStorage.getItem(USER_KEY, true);
        return user || null;
    },
    getMe: () => api.get('/auth/me').then(res => res.data),
    refreshUser: async () => {
        const response = await api.get('/auth/me');
        const user = response.data;
        await secureLocalStorage.setItem(USER_KEY, user);
        // Dispatch event for components listening for user updates (e.g., Layout sidebar)
        window.dispatchEvent(new Event('user-updated'));
        return user;
    },
    regenerateApiKey: () => api.post('/auth/regenerate-api-key').then(res => res.data),
    // Helper to get the current token (for downloads, etc.)
    getToken: () => cachedToken,
};

export const projects = {
    list: () => api.get('/projects').then(res => res.data),
    create: (data) => api.post('/projects', data).then(res => res.data),
    delete: (id) => api.delete(`/projects/${id}`).then(res => res.data),
    getConfig: (id) => api.get(`/projects/${id}/config`).then(res => res.data),
    updateConfig: (id, data) => api.put(`/projects/${id}/config`, data).then(res => res.data),
    uploadFiles: (id, files) => {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        // Don't set Content-Type header - let browser set it with boundary
        return api.post(`/projects/${id}/upload`, formData).then(res => res.data);
    },
    uploadZip: (id, file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post(`/projects/${id}/upload-zip`, formData).then(res => res.data);
    },
    listFiles: (id) => api.get(`/projects/${id}/files`).then(res => res.data),
    deleteFile: (projectId, fileId) => api.delete(`/projects/${projectId}/files/${fileId}`).then(res => res.data),
};

export const compile = {
    start: (projectId, data = {}) => api.post(`/compile/start?project_id=${projectId}`, data).then(res => res.data),
    getStatus: (jobId) => api.get(`/compile/${jobId}/status`).then(res => res.data),
    listJobs: (projectId) => api.get('/compile/jobs', { params: { project_id: projectId } }).then(res => res.data),
    download: async (jobId, filename) => {
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
    list: (projectId) => api.get('/licenses', { params: { project_id: projectId } }).then(res => res.data),
    create: (data) => api.post('/licenses', data).then(res => res.data),
    revoke: (id) => api.post(`/licenses/${id}/revoke`).then(res => res.data),
    delete: (id) => api.delete(`/licenses/${id}`).then(res => res.data),
    getBindings: (id) => api.get(`/licenses/${id}/bindings`).then(res => res.data),
    removeBinding: (licenseId, bindingId) => api.delete(`/licenses/${licenseId}/bindings/${bindingId}`).then(res => res.data),
    // HWID Reset
    resetHwid: (id, reason) => api.post(`/licenses/${id}/reset-hwid`, { reason }).then(res => res.data),
    getResetHistory: (id) => api.get(`/licenses/${id}/reset-history`).then(res => res.data),
    getResetStatus: (id) => api.get(`/licenses/${id}/reset-status`).then(res => res.data),
};

export const webhooks = {
    list: () => api.get('/webhooks').then(res => res.data),
    create: (data) => api.post('/webhooks', data).then(res => res.data),
    get: (id) => api.get(`/webhooks/${id}`).then(res => res.data),
    update: (id, data) => api.put(`/webhooks/${id}`, data).then(res => res.data),
    delete: (id) => api.delete(`/webhooks/${id}`).then(res => res.data),
    getDeliveries: (id, limit = 50) => api.get(`/webhooks/${id}/deliveries`, { params: { limit } }).then(res => res.data),
    test: (id) => api.post(`/webhooks/${id}/test`).then(res => res.data),
    getEvents: () => api.get('/webhooks/events/list').then(res => res.data),
};

export const stats = {
    getDashboard: () => api.get('/stats/dashboard').then(res => res.data),
    getValidations: (days = 7) => api.get('/stats/validations', { params: { days } }).then(res => res.data),
    getGeographic: (days = 30) => api.get('/stats/geographic', { params: { days } }).then(res => res.data),
    getRecentGeographic: (limit = 20) => api.get('/stats/geographic/recent', { params: { limit } }).then(res => res.data),
    // Mission Control Live Map
    getMapData: () => api.get('/analytics/map-data').then(res => res.data),
};

// Admin API (admin role required)
export const admin = {
    getStats: () => api.get('/admin/stats').then(res => res.data),
    getUsers: () => api.get('/admin/users').then(res => res.data),
    getAnalytics: (days = 30) => api.get('/admin/analytics', { params: { days } }).then(res => res.data),
    // New endpoints
    getRevenue: () => api.get('/admin/revenue').then(res => res.data),
    getSystemHealth: () => api.get('/admin/system-health').then(res => res.data),
    updateUserPlan: (userId, plan) => api.put(`/admin/users/${userId}/plan`, { plan }).then(res => res.data),
    updateUserRole: (userId, role) => api.put(`/admin/users/${userId}/role`, { role }).then(res => res.data),
    banUser: (userId) => api.post(`/admin/users/${userId}/ban`).then(res => res.data),
};

// Dodo Payments/Subscription API
export const subscription = {
    getStatus: () => api.get('/subscription/status').then(res => res.data),
    createCheckoutSession: (productId, successUrl, cancelUrl) =>
        api.post('/dodo/create-checkout-session', { product_id: productId, success_url: successUrl, cancel_url: cancelUrl }).then(res => res.data),
};

export const sellers = {
    getProfile: () => api.get('/sellers/me').then(res => res.data),
    onboard: (data) => api.post('/sellers/onboard', data).then(res => res.data),
    updateMonetization: (projectId, data) => api.put(`/projects/${projectId}/monetization`, data).then(res => res.data),
};

// Public Store API (no auth required) - uses different base URL
const publicApi = axios.create({
    baseURL: isTauri ? `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1` : '/api/v1',
    headers: { 'Content-Type': 'application/json' },
});

// Cloud Build API
export const cloudBuild = {
    // Start a cloud build
    start: (projectId, data = {}) => 
        api.post('/cloud-build/start', { project_id: projectId, ...data }).then(res => res.data),
    
    // Get build status with stage progress
    getStatus: (buildId) => 
        api.get(`/cloud-build/${buildId}/status`).then(res => res.data),
    
    // Cancel a running build
    cancel: (buildId) => 
        api.post(`/cloud-build/${buildId}/cancel`).then(res => res.data),
    
    // Retry a failed build
    retry: (buildId) => 
        api.post(`/cloud-build/${buildId}/retry`).then(res => res.data),
    
    // Cleanup build artifacts
    cleanup: (buildId) => 
        api.post(`/cloud-build/${buildId}/cleanup`).then(res => res.data),
    
    // Get build history
    getHistory: (limit = 20, offset = 0) => 
        api.get('/cloud-build/history', { params: { limit, offset } }).then(res => res.data),
    
    // Get artifacts for a build (deprecated - use getStatus instead)
    getArtifacts: (buildId) => 
        api.get(`/cloud-build/${buildId}/status`).then(res => res.data.artifacts),
};

export const publicStore = {
    getProject: (storeSlug) => publicApi.get(`/public/store/${storeSlug}`).then(res => res.data),
    purchaseLicense: (storeSlug, buyerEmail, buyerName, successUrl, cancelUrl) =>
        publicApi.post('/public/purchase', {
            store_slug: storeSlug,
            buyer_email: buyerEmail,
            buyer_name: buyerName,
            success_url: successUrl,
            cancel_url: cancelUrl
        }).then(res => res.data),
    getLicensePortal: (licenseKey) => publicApi.get(`/public/license/${licenseKey}`).then(res => res.data),
};

// Marketplace Store API (public, no auth required)
export const store = {
    // List all marketplace products with optional filters
    listProducts: (params = {}) => {
        const queryParams = new URLSearchParams();
        if (params.category) queryParams.append('category', params.category);
        if (params.language) queryParams.append('language', params.language);
        if (params.min_price !== undefined) queryParams.append('min_price', params.min_price);
        if (params.max_price !== undefined) queryParams.append('max_price', params.max_price);
        if (params.search) queryParams.append('search', params.search);
        if (params.sort) queryParams.append('sort', params.sort);
        if (params.skip !== undefined) queryParams.append('skip', params.skip);
        if (params.limit !== undefined) queryParams.append('limit', params.limit);
        const query = queryParams.toString();
        return publicApi.get(`/store/products${query ? '?' + query : ''}`).then(res => res.data);
    },
    
    // Get single product details
    getProduct: (productId) => publicApi.get(`/store/products/${productId}`).then(res => res.data),
    
    // Get list of categories with counts
    getCategories: () => publicApi.get('/store/categories').then(res => res.data),
    
    // Create checkout session (redirects buyer to Dodo payment page)
    createCheckout: (productId, buyerEmail) => 
        publicApi.post(`/store/checkout/${productId}`, { buyer_email: buyerEmail }).then(res => res.data),
};

export default api;


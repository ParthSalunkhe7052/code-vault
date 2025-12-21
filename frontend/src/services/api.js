import axios from 'axios';

const TOKEN_KEY = 'license_wrapper_token';
const USER_KEY = 'license_wrapper_user';

// Detect if running in Tauri desktop app
const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

// In Tauri, we need the full URL since there's no Vite proxy
// In browser dev mode, use relative path (Vite proxy handles it)
const API_BASE_URL = isTauri
    ? 'http://localhost:8000/api/v1'  // Direct to backend server
    : '/api/v1';                       // Vite proxy in dev

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to include the JWT token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
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
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export const auth = {
    login: async (email, password) => {
        const response = await api.post('/auth/login', { email, password });
        const { access_token, user } = response.data;
        localStorage.setItem(TOKEN_KEY, access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        return user;
    },
    register: async (email, password, name) => {
        const response = await api.post('/auth/register', { email, password, name });
        const { access_token, user } = response.data;
        localStorage.setItem(TOKEN_KEY, access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        return user;
    },
    logout: () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    },
    isAuthenticated: () => {
        return !!localStorage.getItem(TOKEN_KEY);
    },
    getUser: () => {
        const user = localStorage.getItem(USER_KEY);
        return user ? JSON.parse(user) : null;
    },
    getMe: () => api.get('/auth/me').then(res => res.data),
    refreshUser: async () => {
        const response = await api.get('/auth/me');
        const user = response.data;
        localStorage.setItem(USER_KEY, JSON.stringify(user));
        return user;
    },
    regenerateApiKey: () => api.post('/auth/regenerate-api-key').then(res => res.data),
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
        const token = localStorage.getItem(TOKEN_KEY);
        // Use proper URL based on environment (Tauri vs browser)
        const baseUrl = isTauri ? 'http://localhost:8000' : '';
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
        a.download = filename || 'download';
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
};

// Stripe/Subscription API
export const subscription = {
    getStatus: () => api.get('/subscription/status').then(res => res.data),
    createCheckoutSession: (priceId, successUrl, cancelUrl) =>
        api.post('/stripe/create-checkout-session', { price_id: priceId, success_url: successUrl, cancel_url: cancelUrl }).then(res => res.data),
    createCustomerPortal: (returnUrl) =>
        api.post('/stripe/create-customer-portal', { return_url: returnUrl }).then(res => res.data),
};

// Public Store API (no auth required) - uses different base URL
const publicApi = axios.create({
    baseURL: isTauri ? 'http://localhost:8000/api/v1' : '/api/v1',
    headers: { 'Content-Type': 'application/json' },
});

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

export default api;


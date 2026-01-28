import api from './api';

let pricingConfig = null;

export const pricingService = {
    /**
     * Fetch pricing configuration from the backend.
     * Caches the result to avoid redundant requests.
     */
    async getConfig() {
        if (pricingConfig) return pricingConfig;
        try {
            const response = await api.get('/config/pricing');
            pricingConfig = response.data;
            return pricingConfig;
        } catch (error) {
            console.error('Failed to fetch pricing config:', error);
            throw error;
        }
    },

    /**
     * Get configuration for a specific plan.
     * @param {string} plan - 'free', 'pro', or 'enterprise'
     */
    async getPlanConfig(plan) {
        const config = await this.getConfig();
        return config[plan.toLowerCase()];
    }
};

// @ts-nocheck
import api from './api';

// Cache pricing configuration to avoid repeated calls
let pricingConfig = null;

export const pricingService = {
    /**
     * Fetch pricing configuration from backend (public endpoint)
     * Includes Plans, Features, and Limits
     */
    async getConfig() {
        if (pricingConfig) return pricingConfig;
        
        try {
            const response = await api.get('/config/pricing');
            pricingConfig = response.data;
            return pricingConfig;
        } catch (error) {
            console.error('Failed to load pricing config:', error);
            // Fallback to default structure if API fails
            return null;
        }
    },

    /**
     * Get details for a specific plan
     */
    async getPlanConfig(plan) {
        const config = await this.getConfig();
        if (!config || !config.plans) return null;
        return config.plans[plan];
    }
};

export default pricingService;
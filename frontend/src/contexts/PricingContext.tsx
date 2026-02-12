import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import api, { subscription } from '../services/api';
import { useAuth } from './AuthContext';
import { User } from '../types/api';

interface TierLimits {
  maxProjects: number;
  maxLicenses: number;
  buildCredits: number;
  canCloudBuild: boolean;
  offlineLease: boolean;
  analytics?: boolean;
  webhooks?: boolean;
  nodeSupport?: boolean;
}

interface PricingContextType {
  tier: string;
  buildCredits: number;
  limits: TierLimits;
  loading: boolean;
  upgradeToPro: () => void;
  downgradeToFree: () => void;
  createCheckout: (targetTier: string) => Promise<string | undefined>;
  refreshPricing: () => Promise<void>;
  canCreateProject: (currentCount: number) => boolean;
  canCreateLicense: (currentCount: number) => boolean;
  hasBuildCredits: () => boolean;
  consumeBuildCredit: () => boolean;
  getLimits: () => TierLimits;
}

interface BackendLimits {
  max_projects: number;
  max_licenses_per_project: number;
  cloud_builds_per_month: number;
  can_cloud_build: boolean;
  analytics: boolean;
  webhooks: boolean;
  node_support: boolean;
  build_credits_remaining?: number;
}

interface SubscriptionStatus {
  tier?: string;
  usage?: {
    build_credits_remaining?: number;
  };
  limits?: BackendLimits;
}

const PricingContext = createContext<PricingContextType | undefined>(undefined);

export const TIERS = {
  FREE: 'free',
  PRO: 'pro',
  BUSINESS: 'business',
  ENTERPRISE: 'enterprise'
};

// Polar product IDs (must match backend config)
export const POLAR_PRODUCTS: Record<string, string> = {
  [TIERS.PRO]: 'ea01dbfb-e163-4a4a-9c6d-bb9e0892bcb5',
  [TIERS.BUSINESS]: 'd5781651-cff8-44ed-8a3c-7cf42a6512f5',
};

// Default limits (fallback only - real limits come from backend)
const DEFAULT_LIMITS: Record<string, TierLimits> = {
  [TIERS.FREE]: {
    maxProjects: 1,
    maxLicenses: 50,
    buildCredits: 0,
    canCloudBuild: false,
    offlineLease: false
  },
  [TIERS.PRO]: {
    maxProjects: Infinity,
    maxLicenses: 500,
    buildCredits: 25,
    canCloudBuild: true,
    offlineLease: true
  },
  [TIERS.BUSINESS]: {
    maxProjects: Infinity,
    maxLicenses: 5000,
    buildCredits: 100,
    canCloudBuild: true,
    offlineLease: true
  },
  [TIERS.ENTERPRISE]: {
    maxProjects: Infinity,
    maxLicenses: Infinity,
    buildCredits: Infinity,
    canCloudBuild: true,
    offlineLease: true
  }
};

export const PricingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user: authUser } = useAuth();
  const [tier, setTier] = useState<string>(TIERS.FREE);
  const [buildCredits, setBuildCredits] = useState<number>(0);
  const [limits, setLimits] = useState<TierLimits>(DEFAULT_LIMITS[TIERS.FREE]);
  const [loading, setLoading] = useState<boolean>(true);

  // Sync pricing data whenever the authenticated user changes
  useEffect(() => {
    let cancelled = false;

    const syncPricing = async () => {
      if (!authUser) {
        // No user = reset to free defaults
        setTier(TIERS.FREE);
        setLimits(DEFAULT_LIMITS[TIERS.FREE]);
        setBuildCredits(0);
        setLoading(false);
        return;
      }

      try {
        const userPlan = (authUser as User).plan || TIERS.FREE;
        if (!cancelled) setTier(userPlan);

        // Fetch actual limits from backend
        try {
          const response = await api.get('/auth/limits');
          if (!cancelled && response.status === 200) {
            const backendLimits: BackendLimits = response.data;
            setLimits({
              maxProjects: backendLimits.max_projects === -1 ? Infinity : backendLimits.max_projects,
              maxLicenses: backendLimits.max_licenses_per_project === -1 ? Infinity : backendLimits.max_licenses_per_project,
              buildCredits: backendLimits.cloud_builds_per_month === -1 ? Infinity : backendLimits.cloud_builds_per_month,
              canCloudBuild: backendLimits.can_cloud_build,
              offlineLease: userPlan !== TIERS.FREE,
              analytics: backendLimits.analytics,
              webhooks: backendLimits.webhooks,
              nodeSupport: backendLimits.node_support
            });
            setBuildCredits(backendLimits.build_credits_remaining || 0);
          } else if (!cancelled) {
            setLimits(DEFAULT_LIMITS[userPlan] || DEFAULT_LIMITS[TIERS.FREE]);
            setBuildCredits((authUser as User).build_credits || 0);
          }
        } catch {
          if (!cancelled) {
            setLimits(DEFAULT_LIMITS[userPlan] || DEFAULT_LIMITS[TIERS.FREE]);
            setBuildCredits((authUser as User).build_credits || 0);
          }
        }
      } catch (err) {
        console.error('[Pricing] Failed to load user pricing data', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    syncPricing();
    return () => { cancelled = true; };
  }, [authUser]);

  const upgradeToPro = useCallback(() => {
    setTier(TIERS.PRO);
  }, []);

  const downgradeToFree = useCallback(() => {
    setTier(TIERS.FREE);
  }, []);

  /**
   * Create a Polar checkout session and redirect the user.
   * @param {string} targetTier - TIERS.PRO or TIERS.BUSINESS
   * @returns {Promise<string>} checkout URL
   */
  const createCheckout = useCallback(async (targetTier: string): Promise<string | undefined> => {
    const productId = POLAR_PRODUCTS[targetTier];
    if (!productId) throw new Error(`No product ID for tier: ${targetTier}`);

    const data = await subscription.createCheckout(productId);
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    }
    return data.checkout_url;
  }, []);

  /**
   * Refresh pricing data from backend (e.g. after returning from checkout).
   */
  const refreshPricing = useCallback(async () => {
    try {
      const status: SubscriptionStatus = await subscription.getStatus();
      if (status) {
        setTier(status.tier || TIERS.FREE);
        setBuildCredits(status.usage?.build_credits_remaining ?? 0);
        if (status.limits) {
          setLimits({
            maxProjects: status.limits.max_projects === -1 ? Infinity : status.limits.max_projects,
            maxLicenses: status.limits.max_licenses_per_project === -1 ? Infinity : status.limits.max_licenses_per_project,
            buildCredits: status.limits.cloud_builds_per_month === -1 ? Infinity : status.limits.cloud_builds_per_month,
            canCloudBuild: status.limits.can_cloud_build ?? (status.tier !== TIERS.FREE),
            offlineLease: status.tier !== TIERS.FREE,
            analytics: status.limits.analytics,
            webhooks: status.limits.webhooks,
            nodeSupport: status.limits.node_support,
          });
        }
      }
    } catch (err) {
      console.error('[Pricing] Failed to refresh pricing data', err);
    }
  }, []);

  const canCreateProject = useCallback((currentCount: number) => {
    return currentCount < limits.maxProjects;
  }, [limits.maxProjects]);

  const canCreateLicense = useCallback((currentCount: number) => {
    return currentCount < limits.maxLicenses;
  }, [limits.maxLicenses]);

  const hasBuildCredits = useCallback(() => {
    if (tier === TIERS.FREE) return false; 
    return buildCredits > 0 || limits.buildCredits === Infinity;
  }, [tier, buildCredits, limits.buildCredits]);

  const consumeBuildCredit = useCallback(() => {
    if (limits.buildCredits === Infinity) return true;
    if (buildCredits > 0) {
      // Optimistic decrement for immediate UI feedback
      setBuildCredits(prev => prev - 1);
      // Sync with server in the background to get the real count
      refreshPricing().catch(() => { /* silent - optimistic value is still valid */ });
      return true;
    }
    return false;
  }, [limits.buildCredits, buildCredits, refreshPricing]);

  const getLimits = useCallback(() => limits, [limits]);

  const value = useMemo(() => ({
    tier,
    buildCredits,
    limits,
    loading,
    upgradeToPro,
    downgradeToFree,
    createCheckout,
    refreshPricing,
    canCreateProject,
    canCreateLicense,
    hasBuildCredits,
    consumeBuildCredit,
    getLimits
  }), [tier, buildCredits, limits, loading, upgradeToPro, downgradeToFree, createCheckout, refreshPricing, canCreateProject, canCreateLicense, hasBuildCredits, consumeBuildCredit, getLimits]);

  return (
    <PricingContext.Provider value={value}>
      {children}
    </PricingContext.Provider>
  );
};

export const usePricing = (): PricingContextType => {
  const context = useContext(PricingContext);
  if (!context) {
    throw new Error('usePricing must be used within a PricingProvider');
  }
  return context;
};

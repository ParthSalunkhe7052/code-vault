import React, { createContext, useContext, useState, useEffect } from 'react';
import { auth, subscription } from '../services/api';

const PricingContext = createContext();

export const TIERS = {
  FREE: 'free',
  PRO: 'pro',
  BUSINESS: 'business'
};

// Polar product IDs (must match backend config)
export const POLAR_PRODUCTS = {
  [TIERS.PRO]: 'ea01dbfb-e163-4a4a-9c6d-bb9e0892bcb5',
  [TIERS.BUSINESS]: 'd5781651-cff8-44ed-8a3c-7cf42a6512f5',
};

// Default limits (fallback only - real limits come from backend)
const DEFAULT_LIMITS = {
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
  }
};

export const PricingProvider = ({ children }) => {
  const [tier, setTier] = useState(TIERS.FREE);
  const [buildCredits, setBuildCredits] = useState(0);
  const [limits, setLimits] = useState(DEFAULT_LIMITS[TIERS.FREE]);
  const [loading, setLoading] = useState(true);

  // Load User Data from Backend (single source of truth)
  useEffect(() => {
    const initPricing = async () => {
      try {
        const user = await auth.getUser();
        
        if (user) {
          // Use the plan from the database - no client-side overrides
          const userPlan = user.plan || TIERS.FREE;
          setTier(userPlan);
          
          // Fetch actual limits from backend
          try {
            const response = await fetch('/api/v1/auth/limits', {
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
              }
            });
            if (response.ok) {
              const backendLimits = await response.json();
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
            } else {
              // Fallback to default limits if endpoint fails
              setLimits(DEFAULT_LIMITS[userPlan] || DEFAULT_LIMITS[TIERS.FREE]);
              setBuildCredits(user.build_credits || 0);
            }
          } catch {
            // Fallback to default limits
            setLimits(DEFAULT_LIMITS[userPlan] || DEFAULT_LIMITS[TIERS.FREE]);
            setBuildCredits(user.build_credits || 0);
          }
        }
      } catch (err) {
        console.error('[Pricing] Failed to load user pricing data', err);
      } finally {
        setLoading(false);
      }
    };

    initPricing();
    
    // Listen for updates (optional, if other components update user)
    window.addEventListener('user-updated', initPricing);
    return () => window.removeEventListener('user-updated', initPricing);
  }, []);

  const upgradeToPro = () => {
    // This is just for optimistic UI in the mock flow.
    // In reality, this should trigger a backend sync.
    setTier(TIERS.PRO);
  };

  const downgradeToFree = () => {
    setTier(TIERS.FREE);
  };

  /**
   * Create a Polar checkout session and redirect the user.
   * @param {string} targetTier - TIERS.PRO or TIERS.BUSINESS
   * @returns {Promise<string>} checkout URL
   */
  const createCheckout = async (targetTier) => {
    const productId = POLAR_PRODUCTS[targetTier];
    if (!productId) throw new Error(`No product ID for tier: ${targetTier}`);

    const data = await subscription.createCheckout(productId);
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    }
    return data.checkout_url;
  };

  /**
   * Refresh pricing data from backend (e.g. after returning from checkout).
   */
  const refreshPricing = async () => {
    try {
      const status = await subscription.getStatus();
      if (status) {
        setTier(status.tier || TIERS.FREE);
        setBuildCredits(status.usage?.build_credits_remaining ?? 0);
        if (status.limits) {
          setLimits({
            maxProjects: status.limits.max_projects === -1 ? Infinity : status.limits.max_projects,
            maxLicenses: status.limits.max_licenses === -1 ? Infinity : status.limits.max_licenses,
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
  };

  const canCreateProject = (currentCount) => {
    return currentCount < limits.maxProjects;
  };

  const canCreateLicense = (currentCount) => {
    return currentCount < limits.maxLicenses;
  };

  const hasBuildCredits = () => {
    if (tier === TIERS.FREE) return false; 
    return buildCredits > 0 || limits.buildCredits === Infinity;
  };

  const consumeBuildCredit = () => {
    if (limits.buildCredits === Infinity) return true;
    if (buildCredits > 0) {
      setBuildCredits(prev => prev - 1);
      return true;
    }
    return false;
  };

  const getLimits = () => limits;

  return (
    <PricingContext.Provider value={{
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
    }}>
      {children}
    </PricingContext.Provider>
  );
};

export const usePricing = () => {
  const context = useContext(PricingContext);
  if (!context) {
    throw new Error('usePricing must be used within a PricingProvider');
  }
  return context;
};
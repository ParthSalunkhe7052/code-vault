import React, { createContext, useContext, useState, useEffect } from 'react';
import { auth } from '../services/api';

const PricingContext = createContext();

export const TIERS = {
  FREE: 'free',
  PRO: 'pro',
  ENTERPRISE: 'enterprise'
};

const LIMITS = {
  [TIERS.FREE]: {
    maxProjects: 1,
    maxLicenses: 50,
    buildCredits: 0,
    canCloudBuild: false,
    offlineLease: false
  },
  [TIERS.PRO]: {
    maxProjects: Infinity,
    maxLicenses: 200,
    buildCredits: 10,
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

export const PricingProvider = ({ children }) => {
  const [tier, setTier] = useState(TIERS.FREE);
  const [buildCredits, setBuildCredits] = useState(0);
  const [loading, setLoading] = useState(true);

  // Load User Data & Enforce Logic
  useEffect(() => {
    const initPricing = async () => {
      try {
        const user = await auth.getUser();
        
        if (user) {
           // ADMIN OVERRIDE: If admin, FORCE ENTERPRISE
           if (user.role === 'admin') {
               console.log('[Pricing] Admin detected. Forcing Enterprise tier.');
               setTier(TIERS.ENTERPRISE);
               setBuildCredits(Infinity);
           } else {
               // Normal user: Use plan from DB or default to free
               const userPlan = user.plan || TIERS.FREE;
               setTier(userPlan);
               setBuildCredits(user.build_credits || LIMITS[userPlan]?.buildCredits || 0);
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

  const canCreateProject = (currentCount) => {
    return currentCount < LIMITS[tier].maxProjects;
  };

  const canCreateLicense = (currentCount) => {
    return currentCount < LIMITS[tier].maxLicenses;
  };

  const hasBuildCredits = () => {
    if (tier === TIERS.FREE) return false; 
    return buildCredits > 0 || LIMITS[tier].buildCredits === Infinity;
  };

  const consumeBuildCredit = () => {
    if (LIMITS[tier].buildCredits === Infinity) return true;
    if (buildCredits > 0) {
      setBuildCredits(prev => prev - 1);
      return true;
    }
    return false;
  };

  const getLimits = () => LIMITS[tier];

  return (
    <PricingContext.Provider value={{
      tier,
      buildCredits,
      limits: LIMITS[tier],
      loading,
      upgradeToPro,
      downgradeToFree,
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
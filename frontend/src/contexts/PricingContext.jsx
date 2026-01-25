import React, { createContext, useContext, useState, useEffect } from 'react';

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
  // Mock User State - In production this would come from the backend/user profile
  const [tier, setTier] = useState(TIERS.FREE);
  const [buildCredits, setBuildCredits] = useState(0);

  // Initialize credits when tier changes
  useEffect(() => {
    setBuildCredits(LIMITS[tier].buildCredits);
  }, [tier]);

  const upgradeToPro = () => {
    console.log('Pickle Rick: Upgrading to Pro... *Belch*');
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
    if (tier === TIERS.FREE) return false; // Free users can't build
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

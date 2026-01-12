import React, { memo } from 'react';
import { Monitor, Terminal, Lock, Check, ExternalLink } from 'lucide-react';

/**
 * Platform configuration for cross-platform compilation
 */
const PLATFORMS = [
  {
    id: 'windows',
    name: 'Windows',
    icon: Monitor,
    emoji: null,
    description: 'Windows 10/11 (x64)',
    extension: '.exe',
    free: true,
  },
  {
    id: 'macos',
    name: 'macOS',
    icon: null,
    emoji: '🍎',
    description: 'macOS 11+ (Intel x64)',
    extension: '.app',
    free: false,
  },
  {
    id: 'linux',
    name: 'Linux',
    icon: Terminal,
    emoji: null,
    description: 'Ubuntu, Debian, Fedora (x64)',
    extension: '.bin',
    free: false,
  },
];

/**
 * PlatformSelector - Multi-platform selection for cloud builds
 * 
 * @param {string[]} selectedPlatforms - Array of selected platform IDs
 * @param {function} onChange - Callback when selection changes
 * @param {boolean} isPro - Whether user has Pro subscription
 * @param {boolean} disabled - Disable all interactions (e.g., during build)
 */
const PlatformSelector = ({ 
  selectedPlatforms = ['windows'], 
  onChange, 
  isPro = false, 
  disabled = false 
}) => {
  const togglePlatform = (platformId) => {
    if (disabled) return;
    
    const platform = PLATFORMS.find((p) => p.id === platformId);

    // Check if Pro required but user is not Pro
    if (!platform.free && !isPro) {
      // Don't toggle - the UI will show upgrade prompt
      return;
    }

    // Ensure at least one platform is selected
    if (selectedPlatforms.includes(platformId)) {
      // Don't allow deselecting the last platform
      if (selectedPlatforms.length === 1) return;
      onChange(selectedPlatforms.filter((p) => p !== platformId));
    } else {
      onChange([...selectedPlatforms, platformId]);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-medium text-white">Target Platforms</h3>
        <span className="text-xs text-slate-500">
          {selectedPlatforms.length} selected
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {PLATFORMS.map((platform) => {
          const isSelected = selectedPlatforms.includes(platform.id);
          const isLocked = !platform.free && !isPro;
          const IconComponent = platform.icon;

          return (
            <button
              key={platform.id}
              onClick={() => togglePlatform(platform.id)}
              disabled={disabled}
              className={`
                relative p-4 rounded-xl border-2 transition-all text-left
                ${isSelected
                  ? 'border-purple-500 bg-purple-500/10'
                  : 'border-white/10 bg-white/5 hover:border-white/20'
                }
                ${isLocked ? 'opacity-60' : ''}
                ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}
              `}
            >
              {/* Selection indicator */}
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <div className="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
                    <Check size={12} className="text-white" />
                  </div>
                </div>
              )}

              {/* Lock indicator for Pro-only platforms */}
              {isLocked && (
                <div className="absolute top-2 right-2">
                  <div className="w-5 h-5 rounded-full bg-amber-500/20 flex items-center justify-center">
                    <Lock size={10} className="text-amber-400" />
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 mb-2">
                {/* Platform icon */}
                <div className={`
                  w-10 h-10 rounded-lg flex items-center justify-center
                  ${isSelected ? 'bg-purple-500/20' : 'bg-white/10'}
                `}>
                  {platform.emoji ? (
                    <span className="text-xl">{platform.emoji}</span>
                  ) : IconComponent ? (
                    <IconComponent 
                      size={20} 
                      className={isSelected ? 'text-purple-400' : 'text-slate-400'} 
                    />
                  ) : null}
                </div>

                <div>
                  <h4 className="font-medium text-white">{platform.name}</h4>
                  <p className="text-xs text-slate-400">{platform.description}</p>
                </div>
              </div>

              <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/10">
                <span className="text-xs text-slate-500 font-mono">
                  {platform.extension}
                </span>
                {isLocked ? (
                  <span className="text-xs text-amber-400 flex items-center gap-1">
                    <Lock size={10} />
                    Pro
                  </span>
                ) : platform.free ? (
                  <span className="text-xs text-emerald-400">Free</span>
                ) : (
                  <span className="text-xs text-purple-400">Pro</span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Pro upgrade notice for free users */}
      {!isPro && (
        <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Lock size={16} className="text-amber-400" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-amber-300 mb-1">
                Unlock Cross-Platform Builds
              </h4>
              <p className="text-sm text-slate-400 mb-3">
                Compile to macOS and Linux with a Pro subscription. Reach 40% more users!
              </p>
              <a
                href="/pricing"
                className="inline-flex items-center gap-1.5 text-sm text-purple-400 hover:text-purple-300 transition-colors"
              >
                Upgrade to Pro
                <ExternalLink size={14} />
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Multi-platform build note */}
      {selectedPlatforms.length > 1 && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
          <p className="text-sm text-blue-300">
            <strong>Multi-platform build:</strong> Your project will be compiled separately for each platform. 
            You'll get individual download links when complete.
          </p>
        </div>
      )}
    </div>
  );
};

export default memo(PlatformSelector);

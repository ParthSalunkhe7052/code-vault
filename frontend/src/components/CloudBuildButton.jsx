import React, { useState, useEffect, useRef } from 'react';
import { Cloud, Loader2, CheckCircle, XCircle, Download, Monitor, Terminal, X } from 'lucide-react';
import api from '../services/api';

/**
 * Platform configuration for display
 */
const PLATFORM_INFO = {
  windows: { name: 'Windows', emoji: null, icon: Monitor, extension: '.exe' },
  macos: { name: 'macOS', emoji: '🍎', icon: null, extension: '.app' },
  linux: { name: 'Linux', emoji: null, icon: Terminal, extension: '.bin' },
};

/**
 * CloudBuildButton - Trigger cloud builds with multi-platform support
 * 
 * @param {string} projectId - Project ID to build
 * @param {string} licenseId - Optional license ID to bake in
 * @param {string[]} targetPlatforms - Platforms to build for (default: ['windows'])
 * @param {function} onComplete - Callback when build completes
 * @param {string} className - Additional CSS classes
 */
export function CloudBuildButton({ 
  projectId, 
  licenseId, 
  targetPlatforms = ['windows'],
  onComplete, 
  className = "" 
}) {
  const [status, setStatus] = useState('idle'); // idle, starting, building, completed, failed, cancelled
  const [buildId, setBuildId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0); // Animated progress for smooth transitions
  const [error, setError] = useState(null);
  
  // For single-platform builds (legacy/simple mode)
  const [downloadUrl, setDownloadUrl] = useState(null);
  
  // For multi-platform builds
  const [platformArtifacts, setPlatformArtifacts] = useState({});
  const isMultiPlatform = targetPlatforms.length > 1;
  
  // Polling interval ref for cleanup
  const pollIntervalRef = useRef(null);

  // Animated progress effect - smoothly animate to target progress
  useEffect(() => {
    if (displayProgress < progress) {
      const diff = progress - displayProgress;
      const step = Math.max(1, Math.ceil(diff / 10));
      const timer = setTimeout(() => {
        setDisplayProgress(prev => Math.min(prev + step, progress));
      }, 100);
      return () => clearTimeout(timer);
    } else if (displayProgress > progress) {
      // Allow progress to decrease if needed (e.g., on reset)
      setDisplayProgress(progress);
    }
  }, [progress, displayProgress]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
      }
    };
  }, []);

  const startBuild = async () => {
    setStatus('starting');
    setError(null);
    setProgress(0);
    setDownloadUrl(null);
    setPlatformArtifacts({});
    
    try {
      // Always use the same endpoint - backend handles both single and multi-platform
      const endpoint = '/cloud-build/start';
      
      // Backend expects target_platforms as an array always
      const payload = {
        project_id: projectId,
        license_id: licenseId,
        target_platforms: targetPlatforms, // Always send as array
      };
      
      const response = await api.post(endpoint, payload);
      
      setBuildId(response.data.build_id);
      setStatus('building');
      
      // Initialize platform artifacts for multi-platform
      if (isMultiPlatform) {
        const initialArtifacts = {};
        targetPlatforms.forEach(p => {
          initialArtifacts[p] = { status: 'pending', progress: 0, downloadUrl: null };
        });
        setPlatformArtifacts(initialArtifacts);
      }
      
      // Start polling for status
      pollStatus(response.data.build_id);
    } catch (err) {
      setStatus('failed');
      setError(err.response?.data?.detail || 'Failed to start build');
      console.error(err);
    }
  };

  const pollStatus = async (id) => {
    const checkStatus = async () => {
      try {
        if (isMultiPlatform) {
          // Poll multi-platform artifacts endpoint
          const response = await api.get(`/cloud-build/${id}/artifacts`);
          const artifacts = response.data;
          
          // Update platform artifacts state
          const updatedArtifacts = {};
          let totalProgress = 0;
          let completedCount = 0;
          let failedCount = 0;
          
          artifacts.forEach(artifact => {
            updatedArtifacts[artifact.platform] = {
              status: artifact.status,
              progress: artifact.status === 'completed' ? 100 : (artifact.status === 'running' ? 50 : 0),
              downloadUrl: artifact.download_url,
              filename: artifact.filename,
              error: artifact.error,
            };
            
            if (artifact.status === 'completed') {
              completedCount++;
              totalProgress += 100;
            } else if (artifact.status === 'failed') {
              failedCount++;
              totalProgress += 100; // Count as done for progress
            } else if (artifact.status === 'running') {
              totalProgress += 50;
            }
          });
          
          setPlatformArtifacts(updatedArtifacts);
          setProgress(Math.round(totalProgress / targetPlatforms.length));
          
          // Check if all platforms are done
          const allDone = completedCount + failedCount === targetPlatforms.length;
          if (allDone) {
            if (failedCount === targetPlatforms.length) {
              setStatus('failed');
              setError('All platform builds failed');
            } else {
              setStatus('completed');
              if (onComplete) onComplete({ artifacts: updatedArtifacts });
            }
            return; // Stop polling
          }
        } else {
          // Single platform - use existing status endpoint
          const response = await api.get(`/cloud-build/${id}/status`);
          const { 
            status: buildStatus, 
            progress: buildProgress, 
            download_url, 
            download_key,  // Backward compatibility
            error: buildError,
            artifacts  // Also check artifacts for error/download
          } = response.data;
          
          setProgress(buildProgress || 0);
          
          // Get download URL from artifacts if not at build level
          let finalDownloadUrl = download_url || download_key;
          let finalError = buildError;
          
          if (artifacts && artifacts.length > 0) {
            const artifact = artifacts[0];
            if (!finalDownloadUrl && artifact.download_url) {
              finalDownloadUrl = artifact.download_url;
            }
            if (!finalError && artifact.error) {
              finalError = artifact.error;
            }
          }
          
          if (buildStatus === 'completed') {
            setStatus('completed');
            setDownloadUrl(finalDownloadUrl);
            if (onComplete) onComplete(response.data);
            return; // Stop polling
          } else if (buildStatus === 'failed') {
            setStatus('failed');
            setError(finalError || "Build failed - check GitHub Actions logs for details");
            return; // Stop polling
          }
        }
        
        // Continue polling
        pollIntervalRef.current = setTimeout(checkStatus, 3000);
      } catch (err) {
        console.error('Status check failed:', err);
        // Don't stop polling on transient network errors, but backoff
        pollIntervalRef.current = setTimeout(checkStatus, 5000);
      }
    };
    
    checkStatus();
  };

  const resetBuild = () => {
    setStatus('idle');
    setError(null);
    setProgress(0);
    setDisplayProgress(0);
    setDownloadUrl(null);
    setPlatformArtifacts({});
    setBuildId(null);
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current);
    }
  };

  const cancelBuild = async () => {
    if (!buildId || status !== 'building') return;
    
    try {
      await api.post(`/cloud-build/${buildId}/cancel`);
      setStatus('cancelled');
      setError('Build cancelled by user');
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
      }
    } catch (err) {
      console.error('Failed to cancel build:', err);
      setError(err.response?.data?.detail || 'Failed to cancel build');
    }
  };

  // Get button text based on platforms
  const getButtonText = () => {
    if (isMultiPlatform) {
      return `Build for ${targetPlatforms.length} Platforms`;
    }
    const platform = PLATFORM_INFO[targetPlatforms[0]] || PLATFORM_INFO.windows;
    return `Build for ${platform.name}`;
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {status === 'idle' && (
        <button
          onClick={startBuild}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg font-medium transition-all shadow-lg hover:shadow-purple-500/25 w-full justify-center"
        >
          <Cloud className="w-5 h-5" />
          {getButtonText()}
        </button>
      )}

      {status === 'starting' && (
        <div className="flex items-center justify-center gap-2 text-slate-400 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
          <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
          <span>Starting cloud environment...</span>
        </div>
      )}

      {status === 'building' && (
        <div className="space-y-3 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-blue-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="font-medium">
                {isMultiPlatform ? 'Compiling for multiple platforms...' : 'Compiling in cloud...'}
              </span>
            </div>
            <span className="text-sm text-slate-400">{displayProgress}%</span>
          </div>
          
          {/* Overall progress bar */}
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300 ease-out relative"
              style={{ width: `${Math.max(5, displayProgress)}%` }}
            >
              <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
            </div>
          </div>
          
          {/* Per-platform status for multi-platform builds */}
          {isMultiPlatform && Object.keys(platformArtifacts).length > 0 && (
            <div className="space-y-2 mt-3 pt-3 border-t border-slate-700">
              {targetPlatforms.map(platformId => {
                const artifact = platformArtifacts[platformId] || { status: 'pending' };
                const platform = PLATFORM_INFO[platformId];
                const IconComponent = platform?.icon;
                
                return (
                  <div key={platformId} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      {platform?.emoji ? (
                        <span className="text-base">{platform.emoji}</span>
                      ) : IconComponent ? (
                        <IconComponent size={16} className="text-slate-400" />
                      ) : null}
                      <span className="text-slate-300">{platform?.name || platformId}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {artifact.status === 'pending' && (
                        <span className="text-slate-500">Waiting...</span>
                      )}
                      {artifact.status === 'running' && (
                        <span className="text-blue-400 flex items-center gap-1">
                          <Loader2 size={12} className="animate-spin" />
                          Building...
                        </span>
                      )}
                      {artifact.status === 'completed' && (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <CheckCircle size={12} />
                          Done
                        </span>
                      )}
                      {artifact.status === 'failed' && (
                        <span className="text-red-400 flex items-center gap-1">
                          <XCircle size={12} />
                          Failed
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          
          <p className="text-xs text-slate-500 text-center">
            {isMultiPlatform 
              ? 'Multi-platform builds may take 5-10 minutes' 
              : 'This usually takes 2-5 minutes'}
          </p>
          
          {/* Cancel button */}
          <button
            onClick={cancelBuild}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm transition-colors"
          >
            <X className="w-4 h-4" />
            Cancel Build
          </button>
        </div>
      )}

      {status === 'cancelled' && (
        <div className="space-y-3 p-4 bg-amber-500/10 rounded-lg border border-amber-500/20">
          <div className="flex items-center gap-2 text-amber-400 font-medium">
            <XCircle className="w-5 h-5" />
            Build cancelled
          </div>
          <button
            onClick={resetBuild}
            className="text-sm text-amber-400 hover:text-amber-300 underline underline-offset-4"
          >
            Start new build
          </button>
        </div>
      )}

      {status === 'completed' && (
        <div className="space-y-3 p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
          <div className="flex items-center gap-2 text-emerald-400 font-medium">
            <CheckCircle className="w-5 h-5" />
            {isMultiPlatform ? 'All builds completed!' : 'Build completed successfully!'}
          </div>
          
          {/* Single platform download */}
          {!isMultiPlatform && downloadUrl && (
            <a
              href={downloadUrl}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors w-full"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Download className="w-4 h-4" />
              Download Executable
            </a>
          )}
          
          {/* Multi-platform downloads */}
          {isMultiPlatform && (
            <div className="space-y-2">
              {targetPlatforms.map(platformId => {
                const artifact = platformArtifacts[platformId];
                const platform = PLATFORM_INFO[platformId];
                const IconComponent = platform?.icon;
                
                if (!artifact) return null;
                
                return (
                  <div 
                    key={platformId} 
                    className="flex items-center justify-between p-2 bg-black/20 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      {platform?.emoji ? (
                        <span className="text-lg">{platform.emoji}</span>
                      ) : IconComponent ? (
                        <IconComponent size={18} className="text-slate-400" />
                      ) : null}
                      <div>
                        <span className="text-white text-sm">{platform?.name}</span>
                        <span className="text-slate-500 text-xs ml-2">{platform?.extension}</span>
                      </div>
                    </div>
                    
                    {artifact.status === 'completed' && artifact.downloadUrl ? (
                      <a
                        href={artifact.downloadUrl}
                        className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-lg transition-colors"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Download size={14} />
                        Download
                      </a>
                    ) : artifact.status === 'failed' ? (
                      <span className="text-sm text-red-400">Failed</span>
                    ) : (
                      <span className="text-sm text-slate-500">N/A</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          
          {/* Build again button */}
          <button
            onClick={resetBuild}
            className="text-sm text-slate-400 hover:text-slate-300 underline underline-offset-4 w-full text-center mt-2"
          >
            Build again
          </button>
        </div>
      )}

      {status === 'failed' && (
        <div className="space-y-3 p-4 bg-red-500/10 rounded-lg border border-red-500/20">
          <div className="flex items-center gap-2 text-red-400 font-medium">
            <XCircle className="w-5 h-5" />
            Build failed
          </div>
          <p className="text-sm text-red-300 bg-red-950/30 p-2 rounded">{error}</p>
          <button
            onClick={resetBuild}
            className="text-sm text-red-400 hover:text-red-300 underline underline-offset-4"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect, useRef, useCallback } from 'react';
import { Cloud, Loader2, CheckCircle, XCircle, Download, Monitor, Terminal, X, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { useProjectBuild } from '../contexts/BuildContext';
import { useAuth } from '../contexts/AuthContext';

/**
 * Platform configuration for display
 */
const PLATFORM_INFO = {
  windows: { name: 'Windows', emoji: null, icon: Monitor, extension: '.exe' },
  macos: { name: 'macOS', emoji: null, icon: null, extension: '.app' },
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
  // Global Build Context and Auth
  const projectBuild = useProjectBuild(projectId);
  const { isAdmin } = useAuth();

  // Local state (synced with global where possible, but kept for granular UI control)
  const [status, setStatus] = useState('idle'); // idle, starting, building, completed, failed, cancelled
  const [buildId, setBuildId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0); // Animated progress for smooth transitions
  const [error, setError] = useState(null);
  const [stage, setStage] = useState('');
  const [adminErrorDetails, setAdminErrorDetails] = useState(null);
  const [showAdminDetails, setShowAdminDetails] = useState(false);
  
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
    setAdminErrorDetails(null);
    setShowAdminDetails(false);
    setProgress(5); // Start at 5% for immediate feedback
    setDisplayProgress(5);
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
      const newBuildId = response.data.build_id;
      
      setBuildId(newBuildId);
      setStatus('building');
      
      // Sync with Global Context
      if (projectBuild && projectBuild.start) {
          projectBuild.start(newBuildId);
      }
      
      // Initialize platform artifacts for multi-platform
      if (isMultiPlatform) {
        const initialArtifacts = {};
        targetPlatforms.forEach(p => {
          initialArtifacts[p] = { status: 'pending', progress: 0, downloadUrl: null };
        });
        setPlatformArtifacts(initialArtifacts);
      }
      
      // Start polling for status
      pollStatus(newBuildId);
    } catch (err) {
      setStatus('failed');
      
      // Handle admin error details
      const errorDetail = err.response?.data?.detail;
      if (isAdmin && typeof errorDetail === 'object' && errorDetail.traceback) {
        setError(errorDetail.message || errorDetail.error || 'Failed to start build');
        setAdminErrorDetails({
          error: errorDetail.error,
          traceback: errorDetail.traceback,
          buildId: errorDetail.build_id
        });
      } else {
        setError(typeof errorDetail === 'string' ? errorDetail : 'Failed to start build');
        setAdminErrorDetails(null);
      }
      
      console.error('Cloud Build Error:', err);
    }
  };

  const pollStatus = useCallback(async (id) => {
    let pollCount = 0;
    
    const checkStatus = async () => {
      try {
        pollCount++;
        // Sync with Cloud Build every 5th poll (15 seconds) to ensure status accuracy
        const shouldSync = pollCount % 5 === 0;
        
        if (isMultiPlatform) {
          // Poll unified build status endpoint and read artifacts from response
          const response = await api.get(`/cloud-build/${id}/status${shouldSync ? '?sync=true' : ''}`);
          const artifacts = response.data?.artifacts || [];
          if (response.data?.stage) {
            setStage(response.data.stage);
          }
          
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
            const finalStatus = failedCount === targetPlatforms.length ? 'failed' : 'completed';
            setStatus(finalStatus);
            if (finalStatus === 'failed') {
                // Collect all errors
                const errors = artifacts.filter(a => a.error).map(a => `${a.platform}: ${a.error}`);
                setError(errors.length > 0 ? errors.join('; ') : 'All platform builds failed');
            }
            
            // Sync Global Context (Mocking a single status object for the parent)
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus({
                    status: finalStatus,
                    progress: 100,
                    artifacts: Object.values(updatedArtifacts) // simplified
                });
            }

            if (onComplete) onComplete({ artifacts: updatedArtifacts });
            return; // Stop polling
          }
        } else {
          // Single platform - use existing status endpoint with sync parameter
          const response = await api.get(`/cloud-build/${id}/status${shouldSync ? '?sync=true' : ''}`);
          const { 
            status: buildStatus, 
            progress: buildProgress, 
            download_url, 
            download_key,  // Backward compatibility
            error: buildError,
            artifacts,  // Also check artifacts for error/download
            stage: buildStage
          } = response.data;
          
          setProgress(buildProgress || 0);
          if (buildStage) {
            setStage(buildStage);
          }
          
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
          
          // Handle terminal states
          if (buildStatus === 'completed') {
            setStatus('completed');
            setDownloadUrl(finalDownloadUrl);
            // Sync Global Context
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus(response.data);
            }
            if (onComplete) onComplete(response.data);
            return; // Stop polling
          } else if (buildStatus === 'failed') {
            setStatus('failed');
            setError(finalError || "Build failed - check logs for details");
            // Sync Global Context
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus(response.data);
            }
            return; // Stop polling
          } else if (buildStatus === 'cancelled') {
            setStatus('cancelled');
            setError('Build was cancelled');
            // Sync Global Context
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus(response.data);
            }
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
  }, [isMultiPlatform, targetPlatforms, projectBuild, onComplete]);

  // Sync with Global Context on Mount/Update
  useEffect(() => {
    if (projectBuild && projectBuild.status) {
       if (['pending', 'queued', 'running'].includes(projectBuild.status)) {
           setStatus('building');
           setBuildId(projectBuild.jobId);
           if (typeof projectBuild.progress === 'number') {
             setProgress(projectBuild.progress);
           }
           if (status === 'idle') {
             pollStatus(projectBuild.jobId); // Resume polling
           }
       }
       if (projectBuild.status === 'completed') {
           if (status === 'building') {
             if (pollIntervalRef.current) {
                 // Poller is running, let it finish
             } else if (projectBuild.jobId) {
                 pollStatus(projectBuild.jobId);
             }
           }
       }
       if (projectBuild.status === 'failed') {
           setStatus('failed');
           if (projectBuild.error) {
             setError(projectBuild.error);
           }
       }
       if (projectBuild.status === 'cancelled') {
           setStatus('cancelled');
           setError('Build was cancelled');
       }
    }
  }, [projectBuild?.status, projectBuild?.jobId, projectBuild?.progress, projectBuild?.error, status, pollStatus]);

  const resetBuild = () => {
    setStatus('idle');
    setError(null);
    setAdminErrorDetails(null);
    setShowAdminDetails(false);
    setProgress(0);
    setDisplayProgress(0);
    setDownloadUrl(null);
    setPlatformArtifacts({});
    setBuildId(null);
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    // Clear from global context
    if (projectBuild && projectBuild.cancel) {
      projectBuild.cancel();
    }
  };

const cancelBuild = async () => {
    if (!buildId) return;
    
    // Stop polling immediately
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    
    try {
      setError(null);
      const response = await api.post(`/cloud-build/${buildId}/cancel`);
      
      // Reset to idle immediately - user can start a new build
      resetBuild();
      
    } catch (err) {
      console.error('Failed to cancel build:', err);
      // Even on error, reset so user isn't stuck
      resetBuild();
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
          {stage && (
            <p className="text-xs text-slate-500">{stage}</p>
          )}
          
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
          
          {/* Sync status hint */}
          <p className="text-xs text-slate-500 text-center">
            Status syncs every 15 seconds with Cloud Build
          </p>
        </div>
      )}

{status === 'cancelled' && (
        <div className="space-y-3 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
          <div className="flex items-center gap-2 text-slate-400 font-medium">
            <XCircle className="w-5 h-5" />
            Build cancelled
          </div>
          <button
            onClick={resetBuild}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg font-medium transition-all shadow-lg hover:shadow-purple-500/25 w-full"
          >
            <Cloud className="w-5 h-5" />
            {getButtonText()}
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
          {!isMultiPlatform && (
            downloadUrl ? (
              <a
                href={downloadUrl}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors w-full"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Download className="w-4 h-4" />
                Download Executable
              </a>
            ) : (
              <div className="text-center p-2">
                 <p className="text-sm text-emerald-400 mb-2">Build Successful</p>
                 <span className="text-xs text-slate-400 flex items-center justify-center gap-2">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Finalizing download...
                 </span>
              </div>
            )
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
          
          {/* Admin error details - only shown for admin users */}
          {isAdmin && adminErrorDetails && (
            <div className="mt-3">
              <button
                onClick={() => setShowAdminDetails(!showAdminDetails)}
                className="flex items-center gap-2 text-xs text-amber-400 hover:text-amber-300 mb-2"
              >
                <AlertCircle className="w-3 h-3" />
                {showAdminDetails ? 'Hide' : 'Show'} Admin Debug Info
              </button>
              
              {showAdminDetails && (
                <div className="space-y-2">
                  {adminErrorDetails.buildId && (
                    <p className="text-xs text-slate-400">
                      Build ID: <span className="font-mono text-slate-300">{adminErrorDetails.buildId}</span>
                    </p>
                  )}
                  <div className="bg-black/50 rounded p-2 overflow-auto max-h-48">
                    <p className="text-xs text-slate-500 mb-1">Error:</p>
                    <pre className="text-xs text-red-300 font-mono whitespace-pre-wrap">
                      {adminErrorDetails.error}
                    </pre>
                  </div>
                  {adminErrorDetails.traceback && (
                    <div className="bg-black/50 rounded p-2 overflow-auto max-h-64">
                      <p className="text-xs text-slate-500 mb-1">Traceback:</p>
                      <pre className="text-xs text-amber-300/80 font-mono text-[10px] whitespace-pre-wrap">
                        {adminErrorDetails.traceback}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          
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

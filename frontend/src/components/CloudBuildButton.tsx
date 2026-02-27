import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Cloud, Loader2, CheckCircle, XCircle, Download, Monitor, Terminal, X, AlertCircle, LucideIcon } from 'lucide-react';
import api from '../services/api';
import { useProjectBuild } from '../contexts/BuildContext';
import { useAuth } from '../contexts/AuthContext';

/**
 * Platform configuration for display
 */
interface PlatformMeta {
    name: string;
    emoji: string | null;
    icon: LucideIcon | null;
    extension: string;
}

const PLATFORM_INFO: Record<string, PlatformMeta> = {
  windows: { name: 'Windows', emoji: null, icon: Monitor, extension: '.exe' },
  macos: { name: 'macOS', emoji: null, icon: null, extension: '.app' },
  linux: { name: 'Linux', emoji: null, icon: Terminal, extension: '.bin' },
};

interface CloudBuildButtonProps {
    projectId: string;
    licenseId?: string | undefined;
    targetPlatforms?: string[];
    licenseMode?: string;
    demoDuration?: number;
    onComplete?: (data: any) => void;
    className?: string;
}

/**
 * CloudBuildButton - Trigger cloud builds with multi-platform support
 */
export const CloudBuildButton: React.FC<CloudBuildButtonProps> = ({ 
  projectId, 
  licenseId, 
  targetPlatforms = ['windows'],
  licenseMode = 'generic',
  demoDuration = 60,
  onComplete, 
  className = "" 
}) => {
  const projectBuild = useProjectBuild(projectId);
  const { isAdmin } = useAuth();

  const [status, setStatus] = useState('idle');
  const [buildId, setBuildId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState('');
  const [adminErrorDetails, setAdminErrorDetails] = useState<any>(null);
  const [showAdminDetails, setShowAdminDetails] = useState(false);
  
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [platformArtifacts, setPlatformArtifacts] = useState<Record<string, any>>({});
  const isMultiPlatform = targetPlatforms.length > 1;
  
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (displayProgress < progress) {
      const diff = progress - displayProgress;
      const step = Math.max(1, Math.ceil(diff / 10));
      const timer = setTimeout(() => {
        setDisplayProgress(prev => Math.min(prev + step, progress));
      }, 100);
      return () => clearTimeout(timer);
    } else if (displayProgress > progress) {
      setDisplayProgress(progress);
    }
    return undefined;
  }, [progress, displayProgress]);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
      }
    };
  }, []);

  const pollStatus = useCallback(async (id: string) => {
    let pollCount = 0;
    
    const checkStatus = async () => {
      try {
        pollCount++;
        const shouldSync = pollCount % 5 === 0;
        
        if (isMultiPlatform) {
          const response = await api.get(`/cloud-build/${id}/status${shouldSync ? '?sync=true' : ''}`);
          const artifacts = response.data?.artifacts || [];
          if (response.data?.stage) {
            setStage(response.data.stage);
          }
          
          const updatedArtifacts: Record<string, any> = {};
          let totalProgress = 0;
          let completedCount = 0;
          let failedCount = 0;
          
          artifacts.forEach((artifact: any) => {
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
              totalProgress += 100;
            } else if (artifact.status === 'running') {
              totalProgress += 50;
            }
          });
          
          setPlatformArtifacts(updatedArtifacts);
          setProgress(Math.round(totalProgress / targetPlatforms.length));
          
          const allDone = completedCount + failedCount === targetPlatforms.length;
          if (allDone) {
            const finalStatus = failedCount === targetPlatforms.length ? 'failed' : 'completed';
            setStatus(finalStatus);
            if (finalStatus === 'failed') {
                const errors = artifacts.filter((a: any) => a.error).map((a: any) => `${a.platform}: ${a.error}`);
                setError(errors.length > 0 ? errors.join('; ') : 'All platform builds failed');
            }
            
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus({
                    status: finalStatus,
                    progress: 100,
                    artifacts: Object.values(updatedArtifacts)
                });
            }

            if (onComplete) onComplete({ artifacts: updatedArtifacts });
            return;
          }
        } else {
          const response = await api.get(`/cloud-build/${id}/status${shouldSync ? '?sync=true' : ''}`);
          const { 
            status: buildStatus, 
            progress: buildProgress, 
            download_url, 
            download_key,
            error: buildError,
            artifacts,
            stage: buildStage
          } = response.data;
          
          setProgress(buildProgress || 0);
          if (buildStage) {
            setStage(buildStage);
          }
          
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
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus(response.data);
            }
            if (onComplete) onComplete(response.data);
            return;
          } else if (buildStatus === 'failed') {
            setStatus('failed');
            setError(finalError || "Build failed - check logs for details");
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus(response.data);
            }
            return;
          } else if (buildStatus === 'cancelled') {
            setStatus('cancelled');
            setError('Build was cancelled');
            if (projectBuild && projectBuild.updateStatus) {
                projectBuild.updateStatus(response.data);
            }
            return;
          }
        }
        
        pollIntervalRef.current = setTimeout(checkStatus, 3000);
      } catch (err) {
        console.error('Status check failed:', err);
        pollIntervalRef.current = setTimeout(checkStatus, 5000);
      }
    };
    
    checkStatus();
  }, [isMultiPlatform, targetPlatforms, projectBuild, onComplete]);

  const startBuild = async () => {
    setStatus('starting');
    setError(null);
    setAdminErrorDetails(null);
    setShowAdminDetails(false);
    setProgress(5);
    setDisplayProgress(5);
    setDownloadUrl(null);
    setPlatformArtifacts({});
    
    try {
      const endpoint = '/cloud-build/start';
      const payload = {
        project_id: projectId,
        license_id: licenseId,
        target_platforms: targetPlatforms,
        license_mode: licenseMode,
        demo_duration: demoDuration,
      };
      
      const response = await api.post(endpoint, payload);
      const newBuildId = response.data.build_id;
      
      setBuildId(newBuildId);
      setStatus('building');
      
      if (projectBuild && projectBuild.start) {
          projectBuild.start(newBuildId);
      }
      
      if (isMultiPlatform) {
        const initialArtifacts: Record<string, any> = {};
        targetPlatforms.forEach(p => {
          initialArtifacts[p] = { status: 'pending', progress: 0, downloadUrl: null };
        });
        setPlatformArtifacts(initialArtifacts);
      }
      
      pollStatus(newBuildId);
    } catch (err: any) {
      setStatus('failed');
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
    }
  };

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
    if (projectBuild && projectBuild.cancel) {
      projectBuild.cancel();
    }
  };

  const cancelBuild = async () => {
    if (!buildId) return;
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    try {
      setError(null);
      await api.post(`/cloud-build/${buildId}/cancel`);
      resetBuild();
    } catch (err) {
      console.error('Failed to cancel build:', err);
      resetBuild();
    }
  };

  useEffect(() => {
    if (projectBuild && projectBuild.status) {
       if (['pending', 'queued', 'running'].includes(projectBuild.status)) {
           setStatus('building');
           setBuildId(projectBuild.jobId || null);
           if (typeof projectBuild.progress === 'number') {
             setProgress(projectBuild.progress);
           }
           if (status === 'idle' && projectBuild.jobId) {
             pollStatus(projectBuild.jobId);
           }
       }
       if (projectBuild.status === 'completed' && status === 'building') {
           if (!pollIntervalRef.current && projectBuild.jobId) {
               pollStatus(projectBuild.jobId);
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
  }, [projectBuild, status, pollStatus]);

  const getButtonText = () => {
    if (isMultiPlatform) {
      return `Build for ${targetPlatforms.length} Platforms`;
    }
    const platformId = targetPlatforms[0] || 'windows';
    const platform = PLATFORM_INFO[platformId] || PLATFORM_INFO['windows'];
    return `Build for ${platform!.name}`;
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
          
          <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300 ease-out relative"
              style={{ width: `${Math.max(5, displayProgress)}%` }}
            >
              <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
            </div>
          </div>
          
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
                      {artifact.status === 'pending' && <span className="text-slate-500">Waiting...</span>}
                      {artifact.status === 'running' && (
                        <span className="text-blue-400 flex items-center gap-1">
                          <Loader2 size={12} className="animate-spin" /> Building...
                        </span>
                      )}
                      {artifact.status === 'completed' && (
                        <span className="text-emerald-400 flex items-center gap-1">
                          <CheckCircle size={12} /> Done
                        </span>
                      )}
                      {artifact.status === 'failed' && (
                        <span className="text-red-400 flex items-center gap-1">
                          <XCircle size={12} /> Failed
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          
          <button
            onClick={cancelBuild}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm transition-colors"
          >
            <X className="w-4 h-4" /> Cancel Build
          </button>
        </div>
      )}

      {status === 'cancelled' && (
        <div className="space-y-3 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
          <div className="flex items-center gap-2 text-slate-400 font-medium">
            <XCircle className="w-5 h-5" /> Build cancelled
          </div>
          <button
            onClick={resetBuild}
            className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg font-medium transition-all shadow-lg hover:shadow-purple-500/25 w-full"
          >
            <Cloud className="w-5 h-5" /> {getButtonText()}
          </button>
        </div>
      )}

      {status === 'completed' && (
        <div className="space-y-3 p-4 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
          <div className="flex items-center gap-2 text-emerald-400 font-medium">
            <CheckCircle className="w-5 h-5" /> {isMultiPlatform ? 'All builds completed!' : 'Build completed successfully!'}
          </div>
          
          {!isMultiPlatform && (
            downloadUrl ? (
              <a
                href={downloadUrl}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors w-full"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Download className="w-4 h-4" /> Download Executable
              </a>
            ) : (
              <div className="text-center p-2">
                 <p className="text-sm text-emerald-400 mb-2">Build Successful</p>
                 <span className="text-xs text-slate-400 flex items-center justify-center gap-2">
                    <Loader2 className="w-3 h-3 animate-spin" /> Finalizing download...
                 </span>
              </div>
            )
          )}
          
          {isMultiPlatform && (
            <div className="space-y-2">
              {targetPlatforms.map(platformId => {
                const artifact = platformArtifacts[platformId];
                const platform = PLATFORM_INFO[platformId];
                const IconComponent = platform?.icon;
                if (!artifact) return null;
                return (
                  <div key={platformId} className="flex items-center justify-between p-2 bg-black/20 rounded-lg">
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
                      <a href={artifact.downloadUrl} className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-lg transition-colors" target="_blank" rel="noopener noreferrer">
                        <Download size={14} /> Download
                      </a>
                    ) : (
                      <span className="text-sm text-slate-500">{artifact.status}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          <button onClick={resetBuild} className="text-sm text-slate-400 hover:text-slate-300 underline underline-offset-4 w-full text-center mt-2">Build again</button>
        </div>
      )}

      {status === 'failed' && (
        <div className="space-y-3 p-4 bg-red-500/10 rounded-lg border border-red-500/20">
          <div className="flex items-center gap-2 text-red-400 font-medium">
            <XCircle className="w-5 h-5" /> Build failed
          </div>
          <p className="text-sm text-red-300 bg-red-950/30 p-2 rounded">{error}</p>
          {isAdmin && adminErrorDetails && (
            <div className="mt-3">
              <button onClick={() => setShowAdminDetails(!showAdminDetails)} className="flex items-center gap-2 text-xs text-amber-400 hover:text-amber-300 mb-2">
                <AlertCircle className="w-3 h-3" /> {showAdminDetails ? 'Hide' : 'Show'} Admin Debug Info
              </button>
              {showAdminDetails && (
                <div className="space-y-2">
                  <pre className="text-xs text-red-300 font-mono whitespace-pre-wrap bg-black/50 p-2 rounded">{adminErrorDetails.error}</pre>
                </div>
              )}
            </div>
          )}
          <button onClick={resetBuild} className="text-sm text-red-400 hover:text-red-300 underline underline-offset-4">Try again</button>
        </div>
      )}
    </div>
  );
}

import React, { useState, useEffect, useRef, memo } from 'react';
import { Loader2, CheckCircle, XCircle, Download, Monitor, Terminal, RefreshCw, X, RotateCcw } from 'lucide-react';
import { cloudBuild } from '../../services/api';

/**
 * Platform configuration for display
 */
const PLATFORM_INFO = {
  windows: { name: 'Windows', emoji: null, icon: Monitor, extension: '.exe', color: 'blue' },
  macos: { name: 'macOS', emoji: '🍎', icon: null, extension: '.app', color: 'slate' },
  linux: { name: 'Linux', emoji: null, icon: Terminal, extension: '.bin', color: 'orange' },
};

/**
 * MultiPlatformBuildStatus - Displays build progress for multiple platform artifacts
 * 
 * Use this component when you need standalone status display separate from the build button.
 * The CloudBuildButton already includes inline status, but this can be used for:
 * - Build history pages
 * - Detailed build monitoring
 * - Project dashboard widgets
 * 
 * @param {string} buildId - Build ID to monitor
 * @param {string[]} platforms - List of platforms being built
 * @param {boolean} autoRefresh - Whether to poll for updates (default: true)
 * @param {function} onAllComplete - Callback when all platforms finish
 */
const MultiPlatformBuildStatus = ({ 
  buildId, 
  platforms = ['windows'],
  autoRefresh = true,
  onAllComplete,
  onCancel,
  onRetry,
}) => {
  const [buildStatus, setBuildStatus] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    if (!buildId) return;

    const fetchStatus = async () => {
      try {
        const data = await cloudBuild.getStatus(buildId);
        setBuildStatus(data);
        setArtifacts(data.artifacts || []);
        setLoading(false);
        setError(null);

        // Check if all done
        const allDone = (data.artifacts || []).every(
          a => a.status === 'completed' || a.status === 'failed' || a.status === 'cancelled'
        );
        
        if (allDone && onAllComplete) {
          onAllComplete(data.artifacts);
        }
        
        return allDone || data.status === 'cancelled';
      } catch (err) {
        console.error('Failed to fetch build status:', err);
        setError('Failed to fetch build status');
        setLoading(false);
        return true; // Stop polling on error
      }
    };

    // Initial fetch
    fetchStatus();

    // Set up polling if autoRefresh is enabled
    if (autoRefresh) {
      const poll = async () => {
        const done = await fetchStatus();
        if (!done) {
          pollIntervalRef.current = setTimeout(poll, 3000);
        }
      };
      pollIntervalRef.current = setTimeout(poll, 3000);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
      }
    };
  }, [buildId, autoRefresh, onAllComplete]);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const data = await cloudBuild.getStatus(buildId);
      setBuildStatus(data);
      setArtifacts(data.artifacts || []);
      setError(null);
    } catch (err) {
      setError('Failed to refresh');
    }
    setLoading(false);
  };

  const handleCancel = async () => {
    if (cancelling) return;
    setCancelling(true);
    try {
      await cloudBuild.cancel(buildId);
      handleRefresh();
      onCancel?.();
    } catch (err) {
      console.error('Failed to cancel build:', err);
    }
    setCancelling(false);
  };

  const handleRetry = async () => {
    if (retrying) return;
    setRetrying(true);
    try {
      const result = await cloudBuild.retry(buildId);
      onRetry?.(result.new_build_id);
    } catch (err) {
      console.error('Failed to retry build:', err);
      setError(err.response?.data?.detail || 'Failed to retry build');
    }
    setRetrying(false);
  };

  // Calculate overall progress
  const overallProgress = artifacts.length > 0
    ? Math.round(
        artifacts.reduce((sum, a) => {
          if (a.status === 'completed' || a.status === 'failed') return sum + 100;
          if (a.status === 'running') return sum + 50;
          return sum;
        }, 0) / artifacts.length
      )
    : 0;

  const completedCount = artifacts.filter(a => a.status === 'completed').length;
  const failedCount = artifacts.filter(a => a.status === 'failed').length;
  const cancelledCount = artifacts.filter(a => a.status === 'cancelled').length;
  const isAllDone = completedCount + failedCount + cancelledCount === artifacts.length && artifacts.length > 0;
  const isRunning = artifacts.some(a => a.status === 'running' || a.status === 'pending');
  const hasFailed = failedCount > 0 && isAllDone;

  if (loading && artifacts.length === 0) {
    return (
      <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
        <div className="flex items-center justify-center gap-2 text-slate-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading build status...</span>
        </div>
      </div>
    );
  }

  if (error && artifacts.length === 0) {
    return (
      <div className="p-4 bg-red-500/10 rounded-lg border border-red-500/20">
        <div className="flex items-center justify-between">
          <span className="text-red-400">{error}</span>
          <button
            onClick={handleRefresh}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <RefreshCw size={16} className="text-slate-400" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with overall progress */}
      <div className="flex items-center justify-between">
        <div className="flex flex-col">
          <h3 className="text-base font-medium text-white">Build Progress</h3>
          {/* Stage display from server */}
          {buildStatus?.stage && isRunning && (
            <span className="text-xs text-blue-400 mt-0.5">{buildStatus.stage}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">
            {completedCount}/{artifacts.length} complete
          </span>
          
          {/* Cancel button for running builds */}
          {isRunning && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors disabled:opacity-50"
              title="Cancel build"
            >
              {cancelling ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <X size={12} />
              )}
              Cancel
            </button>
          )}
          
          {/* Retry button for failed builds */}
          {hasFailed && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 rounded-lg transition-colors disabled:opacity-50"
              title="Retry failed build"
            >
              {retrying ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <RotateCcw size={12} />
              )}
              Retry
            </button>
          )}
          
          {!autoRefresh && (
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
            >
              <RefreshCw 
                size={14} 
                className={`text-slate-400 ${loading ? 'animate-spin' : ''}`} 
              />
            </button>
          )}
        </div>
      </div>

      {/* Overall progress bar */}
      {!isAllDone && (
        <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
          <div
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      )}

      {/* Per-platform status */}
      <div className="space-y-2">
        {artifacts.map((artifact) => {
          const platform = PLATFORM_INFO[artifact.platform] || PLATFORM_INFO.windows;
          const IconComponent = platform.icon;

          return (
            <div
              key={artifact.platform}
              className={`
                flex items-center justify-between p-3 rounded-lg border transition-all
                ${artifact.status === 'completed' 
                  ? 'bg-emerald-500/10 border-emerald-500/20' 
                  : artifact.status === 'failed'
                    ? 'bg-red-500/10 border-red-500/20'
                    : artifact.status === 'cancelled'
                      ? 'bg-slate-500/10 border-slate-500/20'
                      : 'bg-slate-800/50 border-slate-700'
                }
              `}
            >
              {/* Platform info */}
              <div className="flex items-center gap-3">
                <div className={`
                  w-10 h-10 rounded-lg flex items-center justify-center
                  ${artifact.status === 'completed' 
                    ? 'bg-emerald-500/20' 
                    : artifact.status === 'failed'
                      ? 'bg-red-500/20'
                      : 'bg-white/10'
                  }
                `}>
                  {platform.emoji ? (
                    <span className="text-xl">{platform.emoji}</span>
                  ) : IconComponent ? (
                    <IconComponent 
                      size={20} 
                      className={
                        artifact.status === 'completed' 
                          ? 'text-emerald-400' 
                          : artifact.status === 'failed'
                            ? 'text-red-400'
                            : 'text-slate-400'
                      } 
                    />
                  ) : null}
                </div>

                <div>
                  <h4 className="font-medium text-white">{platform.name}</h4>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-500">{platform.extension}</span>
                    {artifact.filename && (
                      <span className="text-slate-400 truncate max-w-[150px]">
                        {artifact.filename}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Status and action */}
              <div className="flex items-center gap-3">
                {artifact.status === 'pending' && (
                  <span className="text-sm text-slate-500">Waiting...</span>
                )}
                
                {artifact.status === 'running' && (
                  <div className="flex items-center gap-2 text-blue-400">
                    <Loader2 size={16} className="animate-spin" />
                    <span className="text-sm">{buildStatus?.stage || 'Building...'}</span>
                  </div>
                )}
                
                {artifact.status === 'cancelled' && (
                  <div className="flex items-center gap-2">
                    <X size={16} className="text-slate-400" />
                    <span className="text-sm text-slate-400">Cancelled</span>
                  </div>
                )}
                
                {artifact.status === 'completed' && (
                  <div className="flex items-center gap-2">
                    <CheckCircle size={16} className="text-emerald-400" />
                    {artifact.download_url ? (
                      <a
                        href={artifact.download_url}
                        className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm rounded-lg transition-colors"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Download size={14} />
                        Download
                      </a>
                    ) : (
                      <span className="text-sm text-emerald-400">Complete</span>
                    )}
                  </div>
                )}
                
                {artifact.status === 'failed' && (
                  <div className="flex items-center gap-2">
                    <XCircle size={16} className="text-red-400" />
                    <span className="text-sm text-red-400" title={artifact.error}>
                      Failed
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Error details for failed builds */}
      {failedCount > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <h4 className="text-sm font-medium text-red-400 mb-2">Build Errors:</h4>
          <ul className="space-y-1">
            {artifacts
              .filter(a => a.status === 'failed' && a.error)
              .map(a => (
                <li key={a.platform} className="text-xs text-red-300">
                  <strong>{PLATFORM_INFO[a.platform]?.name}:</strong> {a.error}
                </li>
              ))}
          </ul>
        </div>
      )}

      {/* Success message */}
      {isAllDone && failedCount === 0 && cancelledCount === 0 && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-center">
          <p className="text-emerald-400 font-medium">
            All {completedCount} platform builds completed successfully!
          </p>
        </div>
      )}
      
      {/* Cancelled message */}
      {cancelledCount > 0 && isAllDone && (
        <div className="bg-slate-500/10 border border-slate-500/20 rounded-lg p-3 text-center">
          <p className="text-slate-400 font-medium">
            Build was cancelled. {completedCount > 0 ? `${completedCount} platform(s) completed before cancellation.` : ''}
          </p>
        </div>
      )}
    </div>
  );
};

export default memo(MultiPlatformBuildStatus);

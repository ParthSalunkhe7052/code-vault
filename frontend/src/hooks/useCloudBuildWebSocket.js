/**
 * useCloudBuildWebSocket - Real-time WebSocket hook for cloud build updates
 * 
 * Connects to the backend WebSocket endpoint for live build progress streaming.
 * Falls back to HTTP polling if WebSocket connection fails.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// WebSocket URL configuration
const getWsUrl = (buildId) => {
  // Check for explicit WebSocket URL
  const wsUrl = import.meta.env.VITE_WS_URL;
  if (wsUrl) {
    return `${wsUrl}/api/v1/cloud-build/ws/${buildId}`;
  }
  
  // Derive from API URL
  const apiUrl = import.meta.env.VITE_API_URL;
  if (apiUrl) {
    // Convert http(s) to ws(s)
    const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
    const wsHost = apiUrl.replace(/^https?:\/\//, '');
    return `${wsProtocol}://${wsHost}/api/v1/cloud-build/ws/${buildId}`;
  }
  
  // Local development fallback
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}/api/v1/cloud-build/ws/${buildId}`;
};

/**
 * WebSocket states
 */
export const WS_STATES = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  ERROR: 'error',
};

/**
 * useCloudBuildWebSocket hook
 * 
 * @param {string} buildId - Build ID to subscribe to
 * @param {object} options - Configuration options
 * @param {boolean} options.enabled - Whether to connect (default: true when buildId exists)
 * @param {function} options.onProgress - Callback for progress updates
 * @param {function} options.onLog - Callback for log messages
 * @param {function} options.onStatus - Callback for status changes
 * @param {function} options.onComplete - Callback when build completes
 * @param {function} options.onError - Callback for errors
 * @param {number} options.reconnectAttempts - Max reconnection attempts (default: 3)
 * @param {number} options.reconnectDelay - Delay between reconnects in ms (default: 2000)
 * 
 * @returns {object} - { connectionState, lastMessage, sendMessage, disconnect, reconnect }
 */
export function useCloudBuildWebSocket(buildId, options = {}) {
  const {
    enabled = !!buildId,
    onProgress,
    onLog,
    onStatus,
    onComplete,
    onError,
    reconnectAttempts = 3,
    reconnectDelay = 2000,
  } = options;

  const [connectionState, setConnectionState] = useState(WS_STATES.DISCONNECTED);
  const [lastMessage, setLastMessage] = useState(null);
  
  const wsRef = useRef(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const mountedRef = useRef(true);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!buildId || !enabled || !mountedRef.current) return;
    
    cleanup();
    setConnectionState(WS_STATES.CONNECTING);

    try {
      const url = getWsUrl(buildId);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setConnectionState(WS_STATES.CONNECTED);
        reconnectCountRef.current = 0;
        
        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 25000); // Ping every 25 seconds
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        
        // Handle pong response
        if (event.data === 'pong') return;
        
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);
          
          // Route to appropriate callback
          switch (message.type) {
            case 'progress':
              onProgress?.(message.data);
              break;
            case 'log':
              onLog?.(message.data);
              break;
            case 'status':
              onStatus?.(message.data);
              break;
            case 'complete':
              onComplete?.(message.data);
              break;
            case 'error':
              onError?.(message.data);
              break;
            case 'heartbeat':
              // Server heartbeat - connection is alive
              break;
            default:
              console.debug('[WS] Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('[WS] Failed to parse message:', err);
        }
      };

      ws.onerror = (error) => {
        if (!mountedRef.current) return;
        console.error('[WS] WebSocket error:', error);
        setConnectionState(WS_STATES.ERROR);
      };

      ws.onclose = (event) => {
        if (!mountedRef.current) return;
        setConnectionState(WS_STATES.DISCONNECTED);
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        // Attempt reconnection if not intentional close
        if (event.code !== 1000 && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          console.log(`[WS] Reconnecting... attempt ${reconnectCountRef.current}/${reconnectAttempts}`);
          reconnectTimeoutRef.current = setTimeout(connect, reconnectDelay);
        }
      };
    } catch (err) {
      console.error('[WS] Failed to create WebSocket:', err);
      setConnectionState(WS_STATES.ERROR);
    }
  }, [buildId, enabled, cleanup, onProgress, onLog, onStatus, onComplete, onError, reconnectAttempts, reconnectDelay]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    reconnectCountRef.current = reconnectAttempts; // Prevent auto-reconnect
    cleanup();
    setConnectionState(WS_STATES.DISCONNECTED);
  }, [cleanup, reconnectAttempts]);

  // Manual reconnect
  const reconnect = useCallback(() => {
    reconnectCountRef.current = 0;
    connect();
  }, [connect]);

  // Send message to server
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // Connect on mount / buildId change
  useEffect(() => {
    mountedRef.current = true;
    
    if (enabled && buildId) {
      connect();
    }
    
    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [buildId, enabled, connect, cleanup]);

  return {
    connectionState,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect,
    isConnected: connectionState === WS_STATES.CONNECTED,
    isConnecting: connectionState === WS_STATES.CONNECTING,
  };
}

export default useCloudBuildWebSocket;

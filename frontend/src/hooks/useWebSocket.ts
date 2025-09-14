import { useEffect, useRef, useState } from 'react';
import { TransferProgress } from '../types/index.ts';
import { websocketLogger } from '../utils/logger.ts';

interface UseWebSocketReturn {
  isConnected: boolean;
  lastProgress: TransferProgress | null;
  error: string | null;
}

export const useWebSocket = (transferId: string | null): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastProgress, setLastProgress] = useState<TransferProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!transferId) return;

    const wsUrl = `ws://localhost:8000/ws/transfers/${transferId}`;
    websocketLogger.info(`Connecting to WebSocket: ${wsUrl}`);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      websocketLogger.info(`WebSocket connected for transfer: ${transferId}`);
      setIsConnected(true);
      setError(null);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        websocketLogger.debug(`WebSocket message received for ${transferId}:`, data);
        setLastProgress(data);
      } catch (err) {
        websocketLogger.error(`Failed to parse WebSocket message for ${transferId}:`, err);
        setError('Failed to parse progress data');
      }
    };

    socket.onclose = (event) => {
      websocketLogger.info(`WebSocket disconnected for transfer ${transferId}, code: ${event.code}`);
      setIsConnected(false);
    };

    socket.onerror = (err) => {
      websocketLogger.error(`WebSocket error for transfer ${transferId}:`, err);
      setError('WebSocket connection error');
      setIsConnected(false);
    };

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [transferId]);

  return {
    isConnected,
    lastProgress,
    error
  };
};
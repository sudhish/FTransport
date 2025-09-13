import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { TransferProgress } from '../types/index.ts';

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
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastProgress(data);
      } catch (err) {
        setError('Failed to parse progress data');
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
    };

    socket.onerror = (err) => {
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
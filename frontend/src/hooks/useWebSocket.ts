import { useEffect } from 'react';
import { useBrainStore } from '../store/brainStore';

const WS_URL = 'ws://localhost:8000/ws/brain';

export function useWebSocket() {
  const { setSnapshot, setConnected } = useBrainStore();

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
          console.log('WebSocket connected');
          setConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const snapshot = JSON.parse(event.data);
            setSnapshot(snapshot);
          } catch (err) {
            console.error('Failed to parse snapshot:', err);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setConnected(false);
          reconnectTimeout = setTimeout(connect, 3000);
        };
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        reconnectTimeout = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [setSnapshot, setConnected]);
}

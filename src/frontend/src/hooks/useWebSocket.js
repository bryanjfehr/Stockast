import { useContext } from 'react';
import { WebSocketContext } from '../contexts/WebSocketContext';

/**
 * Custom hook to consume the WebSocket context.
 * This hook provides an easy way to access the WebSocket connection and its state
 * from any component within the WebSocketProvider.
 *
 * @returns {object} The value of the WebSocketContext, which includes the WebSocket instance and connection state.
 * @throws {Error} If the hook is used outside of a component wrapped in a WebSocketProvider.
 */
export const useWebSocket = () => {
  const context = useContext(WebSocketContext);

  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }

  return context;
};

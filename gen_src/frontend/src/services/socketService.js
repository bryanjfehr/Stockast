/**
 * @file This service provides utility functions to create and manage WebSocket connections for the application.
 * @description This service uses the browser's native WebSocket API to be compatible with the FastAPI backend.
 */

/**
 * Establishes a WebSocket connection to a specific endpoint with an auth token.
 * 
 * @param {string} endpoint - The WebSocket endpoint (e.g., '/ws/alerts').
 * @param {string} token - The authentication token.
 * @param {object} callbacks - An object with callback functions.
 * @param {function(Event): void} [callbacks.onOpen] - Callback for when the connection opens.
 * @param {function(MessageEvent): void} [callbacks.onMessage] - Callback for receiving a message.
 * @param {function(Event): void} [callbacks.onError] - Callback for connection errors.
 * @param {function(CloseEvent): void} [callbacks.onClose] - Callback for when the connection closes.
 * @returns {WebSocket} The WebSocket instance.
 */
export const createSocket = (endpoint, token, { onOpen, onMessage, onError, onClose }) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  const host = window.location.host;
  const wsBaseUrl = `${wsProtocol}${host}`;

  if (!token) {
    console.error('WebSocket connection requires a token.');
    // Return a mock object that won't throw errors on method calls like .close()
    return { close: () => {} };
  }

  const wsUrl = `${wsBaseUrl}${endpoint}?token=${token}`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = (event) => {
    console.log('WebSocket opened:', endpoint);
    if (onOpen) {
      onOpen(event);
    }
  };

  ws.onmessage = (event) => {
    // No default logging for messages as they can be noisy.
    // The component using the socket is responsible for handling messages.
    if (onMessage) {
      onMessage(event);
    }
  };

  ws.onerror = (event) => {
    console.error('WebSocket error:', endpoint, event);
    if (onError) {
      onError(event);
    }
  };

  ws.onclose = (event) => {
    console.log('WebSocket closed:', endpoint, 'Code:', event.code, 'Reason:', event.reason);
    if (onClose) {
      onClose(event);
    }
  };

  return ws;
};

/**
 * Safely closes an existing WebSocket connection instance.
 * 
 * @param {WebSocket | null | undefined} socket - The WebSocket instance to close.
 */
export const closeSocket = (socket) => {
  if (socket && socket.readyState !== WebSocket.CLOSING && socket.readyState !== WebSocket.CLOSED) {
    console.log('Closing WebSocket connection...');
    socket.close();
  } else {
    console.log('WebSocket connection already closed or closing.');
  }
};

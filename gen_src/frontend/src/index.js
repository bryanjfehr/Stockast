/**
 * This is the main entry point of the React application.
 * It's responsible for rendering the root component (<App />) and wrapping it with necessary context providers and router.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { WebSocketProvider } from './contexts/WebSocketContext';

// Import global styles
import './styles/main.css';

// Get the root DOM element from the public/index.html file
const rootElement = document.getElementById('root');

// Create a root for the React application using the modern createRoot API
const root = ReactDOM.createRoot(rootElement);

// Render the application. The component tree is wrapped with providers to make their
// features available to all child components.
root.render(
  <React.StrictMode>
    {/* BrowserRouter enables client-side routing for the application */}
    <BrowserRouter>
      {/* AuthProvider manages user authentication state (e.g., user, token) */}
      <AuthProvider>
        {/* WebSocketProvider manages the WebSocket connection for real-time data */}
        <WebSocketProvider>
          {/* App is the root component of the application */}
          <App />
        </WebSocketProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);

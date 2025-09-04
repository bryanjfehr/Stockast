/**
 * @file This file provides a React Context for managing WebSocket connections 
 * for real-time data streams, such as stock prices and user alerts.
 */

import React, { createContext, useState, useEffect, useRef, useMemo } from 'react';
import { useAuth } from '../hooks/useAuth';
import { socketService } from '../services/socketService';

/**
 * WebSocketContext provides WebSocket connection status and data to its children components.
 */
export const WebSocketContext = createContext(null);

/**
 * WebSocketProvider is a component that wraps the application and manages WebSocket 
 * connections based on the user's authentication status.
 * @param {{children: React.ReactNode}} props The component props.
 * @returns {JSX.Element} The provider component.
 */
export const WebSocketProvider = ({ children }) => {
  // State for WebSocket data and connection status
  const [latestAlertMessage, setLatestAlertMessage] = useState(null);
  const [latestStockPriceMessage, setLatestStockPriceMessage] = useState(null);
  const [isAlertsConnected, setIsAlertsConnected] = useState(false);
  const [isStocksConnected, setIsStocksConnected] = useState(false);

  // Refs to hold WebSocket instances
  const alertWsRef = useRef(null);
  const stocksWsRef = useRef(null);

  // Auth hook to determine if a user is logged in
  const { token, isAuthenticated, loading: authLoading } = useAuth();

  // Effect to manage the Alerts WebSocket lifecycle
  useEffect(() => {
    if (isAuthenticated && token && !authLoading) {
      // If authenticated, establish the connection.
      // Close any existing connection first to prevent duplicates.
      if (alertWsRef.current) {
        socketService.closeSocket(alertWsRef.current);
      }

      const ws = socketService.createSocket('/ws/alerts', token, {
        onOpen: () => {
          console.log('Alerts WebSocket connected.');
          setIsAlertsConnected(true);
        },
        onMessage: (event) => {
          try {
            setLatestAlertMessage(JSON.parse(event.data));
          } catch (e) {
            console.error('Failed to parse alert message:', event.data);
            setLatestAlertMessage(event.data); // Fallback to raw data
          }
        },
        onError: (event) => {
          console.error('Alerts WebSocket error:', event);
          setIsAlertsConnected(false);
        },
        onClose: (event) => {
          console.log('Alerts WebSocket closed:', event.code, event.reason);
          setIsAlertsConnected(false);
        },
      });
      alertWsRef.current = ws;
    } else if (!authLoading && alertWsRef.current) {
      // If not authenticated (and auth check is complete), close the connection.
      socketService.closeSocket(alertWsRef.current);
      alertWsRef.current = null;
      setIsAlertsConnected(false);
    }

    // Cleanup on component unmount or dependency change
    return () => {
      if (alertWsRef.current) {
        socketService.closeSocket(alertWsRef.current);
        alertWsRef.current = null;
      }
    };
  }, [token, isAuthenticated, authLoading]);

  // Effect to manage the Stocks WebSocket lifecycle
  useEffect(() => {
    if (isAuthenticated && token && !authLoading) {
      // If authenticated, establish the connection.
      if (stocksWsRef.current) {
        socketService.closeSocket(stocksWsRef.current);
      }

      const ws = socketService.createSocket('/ws/stocks/realtime', token, {
        onOpen: () => {
          console.log('Stocks WebSocket connected.');
          setIsStocksConnected(true);
        },
        onMessage: (event) => {
           try {
            setLatestStockPriceMessage(JSON.parse(event.data));
          } catch (e) {
            console.error('Failed to parse stock price message:', event.data);
            setLatestStockPriceMessage(event.data); // Fallback to raw data
          }
        },
        onError: (event) => {
          console.error('Stocks WebSocket error:', event);
          setIsStocksConnected(false);
        },
        onClose: (event) => {
          console.log('Stocks WebSocket closed:', event.code, event.reason);
          setIsStocksConnected(false);
        },
      });
      stocksWsRef.current = ws;
    } else if (!authLoading && stocksWsRef.current) {
      // If not authenticated, close the connection.
      socketService.closeSocket(stocksWsRef.current);
      stocksWsRef.current = null;
      setIsStocksConnected(false);
    }

    // Cleanup on component unmount or dependency change
    return () => {
      if (stocksWsRef.current) {
        socketService.closeSocket(stocksWsRef.current);
        stocksWsRef.current = null;
      }
    };
  }, [token, isAuthenticated, authLoading]);

  // Memoize the context value to prevent unnecessary re-renders of consumers
  const contextValue = useMemo(() => ({
    latestAlertMessage,
    latestStockPriceMessage,
    isAlertsConnected,
    isStocksConnected,
  }), [latestAlertMessage, latestStockPriceMessage, isAlertsConnected, isStocksConnected]);

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

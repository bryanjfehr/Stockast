import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

/**
 * A helper function to format a Unix timestamp into a readable time string.
 * @param {number} timestamp - The Unix timestamp in seconds.
 * @returns {string} - The formatted time string (e.g., '1:30:45 PM').
 */
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  // Assuming the timestamp is in seconds, multiply by 1000 for JavaScript's Date object which expects milliseconds.
  return new Date(timestamp * 1000).toLocaleTimeString();
};

/**
 * AlertPopup component displays trading signal alerts received from the WebSocket
 * as temporary, dismissible popups in the corner of the screen.
 */
const AlertPopup = () => {
  const [alerts, setAlerts] = useState([]);
  const timeoutRefs = useRef({});
  const { latestAlertMessage } = useWebSocket();

  /**
   * Closes an alert popup by its ID, clearing its auto-dismiss timer and removing it from the view.
   * @param {number} alertId - The unique ID of the alert to close.
   */
  const handleClose = (alertId) => {
    // Clear the specific timeout associated with this alert to prevent it from running
    if (timeoutRefs.current[alertId]) {
      clearTimeout(timeoutRefs.current[alertId]);
      delete timeoutRefs.current[alertId];
    }
    // Update the alerts state by filtering out the closed alert
    setAlerts(prevAlerts => prevAlerts.filter(alert => alert.id !== alertId));
  };

  // Effect to process new alert messages from the WebSocket
  useEffect(() => {
    if (latestAlertMessage) {
      try {
        const newAlertData = JSON.parse(latestAlertMessage);

        // Validate that the message has the expected structure for a signal alert
        if (newAlertData.symbol && newAlertData.signal_type && newAlertData.reason && newAlertData.timestamp) {
          const newAlertId = Date.now();
          const newAlert = { id: newAlertId, ...newAlertData };

          setAlerts(prevAlerts => [...prevAlerts, newAlert]);

          // Set a timeout to automatically dismiss this alert after 7 seconds
          const timeoutId = setTimeout(() => {
            handleClose(newAlertId);
          }, 7000);

          // Store the timeout ID in the ref for potential cleanup
          timeoutRefs.current[newAlertId] = timeoutId;
        }
      } catch (error) {
        console.error("Failed to parse WebSocket alert message:", error);
      }
    }
  }, [latestAlertMessage]);

  // Effect for cleaning up timeouts when the component unmounts
  useEffect(() => {
    return () => {
      // Clear all active timeouts to prevent memory leaks
      Object.values(timeoutRefs.current).forEach(clearTimeout);
      timeoutRefs.current = {};
    };
  }, []); // Empty dependency array ensures this runs only on mount and unmount

  // Inline styles for the component
  const containerStyle = {
    position: 'fixed',
    top: '80px', // Position below a potential header
    right: '20px',
    zIndex: 1050, // High z-index to appear above other content
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  };

  const alertStyle = {
    padding: '15px',
    backgroundColor: '#ffffff',
    border: '1px solid #dee2e6',
    borderRadius: '0.375rem',
    boxShadow: '0 0.5rem 1rem rgba(0, 0, 0, 0.15)',
    minWidth: '320px',
    position: 'relative',
    fontFamily: 'sans-serif',
  };

  const closeButtonStyle = {
    position: 'absolute',
    top: '5px',
    right: '10px',
    background: 'transparent',
    border: 'none',
    fontSize: '1.5rem',
    lineHeight: '1',
    cursor: 'pointer',
    color: '#6c757d',
    padding: '0.5rem',
  };

  const getSignalStyle = (signalType) => ({
    fontWeight: 'bold',
    color: signalType === 'BULLISH' ? '#198754' : '#dc3545', // Green for Bullish, Red for Bearish
  });

  return (
    <div style={containerStyle}>
      {alerts.map(alert => (
        <div key={alert.id} style={alertStyle} role="alert">
          <button onClick={() => handleClose(alert.id)} style={closeButtonStyle} aria-label="Close">&times;</button>
          <h5 style={{ margin: '0 0 5px 0', paddingRight: '25px' }}>
            <strong>{alert.symbol}</strong> - <span style={getSignalStyle(alert.signal_type)}>{alert.signal_type}</span>
          </h5>
          <p style={{ margin: '0 0 10px 0' }}>{alert.reason}</p>
          <small style={{ color: '#6c757d' }}>{formatTimestamp(alert.timestamp)}</small>
        </div>
      ))}
    </div>
  );
};

export default AlertPopup;

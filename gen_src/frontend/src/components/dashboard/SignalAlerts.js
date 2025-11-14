import React, { useState, useEffect } from 'react';
// Assuming useWebSocket is a custom hook that provides the latest message from a WebSocket connection.
// It is expected to return an object: { latestAlertMessage: string | null }
import { useWebSocket } from '../../hooks/useWebSocket';

/**
 * A helper function to format a Unix timestamp into a readable date-time string.
 * It handles both millisecond and second precision timestamps.
 * @param {number} timestamp - The Unix timestamp (in seconds or milliseconds).
 * @returns {string} A formatted date-time string (e.g., '01/20 14:35:02').
 */
const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';

    // Heuristic to check if timestamp is in seconds or milliseconds.
    // Timestamps in seconds are typically 10 digits, milliseconds are 13.
    const date = new Date(timestamp > 1000000000000 ? timestamp : timestamp * 1000);

    return date.toLocaleString('en-US', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false, // Using 24-hour format for clarity
    });
};

/**
 * SignalAlerts component displays a list of the most recent trading signal alerts
 * received via WebSocket.
 */
const SignalAlerts = () => {
    // State to store the list of recent alert objects.
    const [alerts, setAlerts] = useState([]);

    // Hook to get the latest message from the WebSocket.
    const { latestAlertMessage } = useWebSocket();

    // Effect to process new alert messages from the WebSocket.
    useEffect(() => {
        if (latestAlertMessage) {
            try {
                const newAlertData = JSON.parse(latestAlertMessage);

                // Validate the structure of the received alert data.
                if (
                    newAlertData &&
                    typeof newAlertData.symbol === 'string' &&
                    typeof newAlertData.signal_type === 'string' &&
                    typeof newAlertData.reason === 'string' &&
                    typeof newAlertData.timestamp === 'number'
                ) {
                    setAlerts(prevAlerts => {
                        // Prepend the new alert to the list.
                        const updatedAlerts = [newAlertData, ...prevAlerts];
                        // Keep only the latest 5 alerts to prevent the list from growing indefinitely.
                        return updatedAlerts.slice(0, 5);
                    });
                } else {
                    console.warn('Received malformed alert message:', newAlertData);
                }
            } catch (err) {
                console.error('Error parsing WebSocket alert message:', latestAlertMessage, err);
            }
        }
    }, [latestAlertMessage]);

    return (
        <div className="signal-alerts-container">
            <h3>Latest Signal Alerts</h3>
            {alerts.length === 0 ? (
                <p className="no-alerts-message">No recent alerts.</p>
            ) : (
                <ul className="alerts-list">
                    {alerts.map((alert, index) => (
                        <li key={`${alert.timestamp}-${alert.symbol}-${index}`} className="alert-item">
                            <div className="alert-header">
                                <span className="alert-symbol">{alert.symbol}</span>
                                <span
                                    className={`alert-signal ${
                                        alert.signal_type === 'BULLISH' ? 'signal-bullish' :
                                        alert.signal_type === 'BEARISH' ? 'signal-bearish' : ''
                                    }`}
                                >
                                    {alert.signal_type}
                                </span>
                            </div>
                            <p className="alert-reason">{alert.reason}</p>
                            <span className="alert-timestamp">{formatTimestamp(alert.timestamp)}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default SignalAlerts;

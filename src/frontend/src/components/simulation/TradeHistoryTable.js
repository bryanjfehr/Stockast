import React from 'react';

/**
 * A helper function to format an ISO timestamp into a readable string.
 * @param {string} timestamp - The ISO 8601 timestamp string.
 * @returns {string} A formatted date-time string (e.g., 'YYYY-MM-DD HH:MM:SS').
 */
const formatTimestamp = (timestamp) => {
  if (!timestamp) return 'N/A';
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  } catch (error) {
    console.error("Error formatting timestamp:", timestamp, error);
    return 'Invalid Timestamp';
  }
};

/**
 * Displays a table listing all the trades executed within a simulation.
 * 
 * @param {object} props - The component props.
 * @param {Array<object>} props.tradeHistory - An array of trade objects.
 *   Each object should have: { id, symbol, action, quantity, price, fee, timestamp }.
 */
const TradeHistoryTable = ({ tradeHistory }) => {

  const styles = {
    container: {
      padding: '20px',
      border: '1px solid #e0e0e0',
      borderRadius: '8px',
      marginTop: '20px',
      backgroundColor: '#ffffff',
      boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    },
    header: {
      marginBottom: '15px',
      color: '#333',
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse',
    },
    th: {
      borderBottom: '2px solid #dee2e6',
      padding: '12px 15px',
      textAlign: 'left',
      backgroundColor: '#f8f9fa',
      fontWeight: '600',
      color: '#495057',
    },
    td: {
      borderBottom: '1px solid #dee2e6',
      padding: '12px 15px',
      textAlign: 'left',
      verticalAlign: 'middle',
    },
    buyAction: {
      color: '#28a745', // Bootstrap success green
      fontWeight: 'bold',
    },
    sellAction: {
      color: '#dc3545', // Bootstrap danger red
      fontWeight: 'bold',
    },
    noHistoryMessage: {
      fontStyle: 'italic',
      color: '#6c757d',
      padding: '20px',
      textAlign: 'center',
    },
  };

  return (
    <div style={styles.container}>
      <h2 style={styles.header}>Trade History</h2>
      {!tradeHistory || tradeHistory.length === 0 ? (
        <p style={styles.noHistoryMessage}>No trade history available for this simulation.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Timestamp</th>
                <th style={styles.th}>Symbol</th>
                <th style={styles.th}>Action</th>
                <th style={styles.th}>Quantity</th>
                <th style={styles.th}>Price</th>
                <th style={styles.th}>Fee</th>
              </tr>
            </thead>
            <tbody>
              {tradeHistory.map((trade) => (
                <tr key={trade.id}>
                  <td style={styles.td}>{formatTimestamp(trade.timestamp)}</td>
                  <td style={styles.td}>{trade.symbol}</td>
                  <td style={trade.action === 'BUY' ? styles.buyAction : styles.sellAction}>
                    {trade.action}
                  </td>
                  <td style={styles.td}>{trade.quantity}</td>
                  <td style={styles.td}>{`$${trade.price.toFixed(2)}`}</td>
                  <td style={styles.td}>{`$${trade.fee.toFixed(2)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TradeHistoryTable;

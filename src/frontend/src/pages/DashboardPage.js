import React from 'react';
import ActiveStocksTable from '../components/dashboard/ActiveStocksTable';
import Watchlist from '../components/dashboard/Watchlist';
import SignalAlerts from '../components/dashboard/SignalAlerts';
import './DashboardPage.css';

/**
 * This page serves as the main user dashboard, displaying active stocks,
 * the user's watchlist, and recent signal alerts.
 * It acts as a layout container for its child components.
 */
const DashboardPage = () => {
  return (
    <div className="dashboard-page-container">
      <div className="dashboard-section">
        <h2>Most Active Stocks</h2>
        <ActiveStocksTable />
      </div>

      <div className="dashboard-section">
        <h2>My Watchlist</h2>
        <Watchlist />
      </div>

      <div className="dashboard-section">
        <h2>Signal Alerts</h2>
        <SignalAlerts />
      </div>
    </div>
  );
};

export default DashboardPage;

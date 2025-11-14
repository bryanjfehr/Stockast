import React, { useState, useEffect, useCallback } from 'react';
import { getSimulationStatus, getSimulationHistory } from '../../api/simulationApi';
import { useAuth } from '../../hooks/useAuth';
import SimulationSetupForm from '../../components/simulation/SimulationSetupForm';
import SimulationPerformanceChart from '../../components/simulation/SimulationPerformanceChart';
import TradeHistoryTable from '../../components/simulation/TradeHistoryTable';

/**
 * SimulationPage allows users to manage and view their trading simulation.
 * It displays the simulation setup form if no simulation is active, or the
 * performance dashboard and trade history if a simulation is running.
 */
const SimulationPage = () => {
    const [simulationData, setSimulationData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const { token, isAuthenticated } = useAuth();

    const fetchSimulationData = useCallback(async () => {
        if (!token || !isAuthenticated) {
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const [statusResponse, historyResponse] = await Promise.all([
                getSimulationStatus(token),
                getSimulationHistory(token)
            ]);

            setSimulationData({ status: statusResponse, history: historyResponse });
        } catch (err) {
            console.error('Error fetching simulation data:', err);

            if (err.response?.status === 404) {
                setSimulationData(null); // No active simulation found, show setup form
                setError(null); // This is an expected state, not an error to display
            } else {
                setError(err.response?.data?.detail || 'Failed to load simulation data.');
            }
        } finally {
            setLoading(false);
        }
    }, [token, isAuthenticated]);

    useEffect(() => {
        if (isAuthenticated && token) {
            fetchSimulationData();
        } else if (!isAuthenticated) {
            setSimulationData(null); // Clear data if not authenticated
            setLoading(false);
            setError(null);
        }
    }, [token, isAuthenticated, fetchSimulationData]);

    /**
     * Callback passed to the setup form to refresh data after a new simulation is started.
     * @param {object} newSimulationResponse - The response from starting a new simulation.
     */
    const handleSimulationStart = (newSimulationResponse) => {
        console.log('New simulation started, refreshing data...', newSimulationResponse);
        fetchSimulationData();
    };

    if (loading) {
        return <div className="simulation-page-container"><p>Loading simulation data...</p></div>;
    }

    return (
        <div className="simulation-page-container" style={{ padding: '20px' }}>
            <h1>Trading Simulation</h1>

            {error && <p style={{ color: 'red' }}>Error: {error}</p>}

            {!error && (
                <>
                    {simulationData ? (
                        <div>
                            <h2>Simulation Overview</h2>
                            <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', flexWrap: 'wrap' }}>
                                <p><strong>Current Capital:</strong> ${simulationData.status?.current_capital?.toFixed(2) || '0.00'}</p>
                                <p>
                                    <strong>Total P&L:</strong> 
                                    <span style={{ color: (simulationData.status?.pnl || 0) >= 0 ? 'green' : 'red' }}>
                                        ${simulationData.status?.pnl?.toFixed(2) || '0.00'}
                                    </span>
                                </p>
                            </div>

                            <h3>Performance History</h3>
                            <SimulationPerformanceChart performanceHistory={simulationData.status?.performance_history || []} />

                            <h3 style={{ marginTop: '40px' }}>Trade History</h3>
                            <TradeHistoryTable tradeHistory={simulationData.history || []} />
                        </div>
                    ) : (
                        <div>
                            <p>No active simulation found. Please set one up to begin.</p>
                            <SimulationSetupForm onSimulationStart={handleSimulationStart} />
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default SimulationPage;

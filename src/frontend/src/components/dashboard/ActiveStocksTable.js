import React, { useState, useEffect } from 'react';
import { getActiveStocks } from '../../api/stockApi.js';

/**
 * A component that fetches and displays a table of the 50 most active TSX stocks.
 */
const ActiveStocksTable = () => {
    const [stocks, setStocks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    /**
     * Fetches active stock data from the API and updates the component's state.
     */
    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getActiveStocks();
            // Ensure stocks is always an array to prevent mapping errors
            setStocks(data || []);
        } catch (err) {
            console.error('Error fetching active stocks:', err);
            // Set a user-friendly error message, using the API's detail if available
            setError(err.response?.data?.detail || 'Failed to load active stocks.');
        } finally {
            setLoading(false);
        }
    };

    // useEffect hook to fetch data when the component mounts.
    // The empty dependency array [] ensures this runs only once.
    useEffect(() => {
        fetchData();
    }, []);

    /**
     * Returns a style object with green for positive numbers and red for negative.
     * @param {number} value The number to check.
     * @returns {object} A style object for inline styling.
     */
    const getChangeStyle = (value) => {
        if (value > 0) return { color: 'green' };
        if (value < 0) return { color: 'red' };
        return {}; // Default color
    };

    /**
     * Renders the main content of the component, including loading/error states
     * and the stocks table itself.
     */
    const renderContent = () => {
        if (loading) {
            return <p>Loading active stocks...</p>;
        }

        if (error) {
            return <p style={{ color: 'red' }}>Error: {error}</p>;
        }

        if (stocks.length === 0) {
            return <p>No active stocks found.</p>;
        }

        return (
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Name</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Change %</th>
                        <th>Volume</th>
                    </tr>
                </thead>
                <tbody>
                    {stocks.map((stock) => (
                        <tr key={stock.symbol}>
                            <td>{stock.symbol}</td>
                            <td>{stock.name}</td>
                            <td>{`$${(stock.price || 0).toFixed(2)}`}</td>
                            <td style={getChangeStyle(stock.change)}>
                                {stock.change > 0 ? `+${(stock.change || 0).toFixed(2)}` : (stock.change || 0).toFixed(2)}
                            </td>
                            <td style={getChangeStyle(stock.percent_change)}>
                                {stock.percent_change > 0 ? `+${(stock.percent_change || 0).toFixed(2)}%` : `${(stock.percent_change || 0).toFixed(2)}%`}
                            </td>
                            <td>{(stock.volume || 0).toLocaleString()}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        );
    };

    return (
        <div className="active-stocks-container">
            <h2>Most Active TSX Stocks</h2>
            {renderContent()}
        </div>
    );
};

export default ActiveStocksTable;

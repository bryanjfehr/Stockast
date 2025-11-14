import React, { useState, useEffect, useCallback } from 'react';
import { getWatchlist, addStockToWatchlist, removeStockFromWatchlist } from '../../api/watchlistApi';
import { useAuth } from '../../hooks/useAuth';
import { useWebSocket } from '../../hooks/useWebSocket';

/**
 * Watchlist component displays the user's stock watchlist.
 * It allows adding and removing stocks and shows real-time price updates via WebSockets.
 */
const Watchlist = () => {
    // STATE
    const [watchlist, setWatchlist] = useState([]);
    const [newStockSymbol, setNewStockSymbol] = useState('');
    const [livePrices, setLivePrices] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // HOOKS
    const { token, isAuthenticated } = useAuth();
    const { latestStockPriceMessage } = useWebSocket();

    // FUNCTIONS

    /**
     * Fetches the user's watchlist from the API.
     * Memoized with useCallback to be used safely in useEffect.
     */
    const fetchWatchlist = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        // Don't set loading to true if we are just refreshing in the background
        // Only show initial loading screen
        if (watchlist.length === 0) {
            setLoading(true);
        }
        setError(null);
        try {
            const data = await getWatchlist(token);
            setWatchlist(data);
        } catch (err) {
            console.error('Error fetching watchlist:', err);
            setError(err.response?.data?.detail || 'Failed to load watchlist.');
        } finally {
            setLoading(false);
        }
    }, [token, watchlist.length]);

    /**
     * Handles the form submission to add a new stock to the watchlist.
     */
    const handleAddStock = async (event) => {
        event.preventDefault();
        const symbolToAdd = newStockSymbol.trim().toUpperCase();
        if (!symbolToAdd || loading) return;

        setLoading(true);
        setError(null);
        try {
            await addStockToWatchlist(symbolToAdd, token);
            setNewStockSymbol('');
            await fetchWatchlist(); // Re-fetch the list to show the new stock
        } catch (err) {
            console.error('Error adding stock:', err);
            setError(err.response?.data?.detail || 'Failed to add stock to watchlist.');
        } finally {
            setLoading(false);
        }
    };

    /**
     * Handles the button click to remove a stock from the watchlist.
     */
    const handleRemoveStock = async (symbol) => {
        if (loading) return;

        setLoading(true);
        setError(null);
        try {
            await removeStockFromWatchlist(symbol, token);
            await fetchWatchlist(); // Re-fetch the list to reflect the removal
        } catch (err) {
            console.error('Error removing stock:', err);
            setError(err.response?.data?.detail || 'Failed to remove stock from watchlist.');
        } finally {
            setLoading(false);
        }
    };

    // EFFECT HOOKS

    // Fetch watchlist on initial mount or when authentication status changes.
    useEffect(() => {
        if (isAuthenticated && token) {
            fetchWatchlist();
        } else if (!isAuthenticated) {
            setWatchlist([]);
            setLoading(false);
            setError(null);
        }
    }, [token, isAuthenticated, fetchWatchlist]);

    // Process incoming WebSocket messages for live price updates.
    useEffect(() => {
        if (latestStockPriceMessage) {
            try {
                const data = JSON.parse(latestStockPriceMessage);
                // Ensure the message is a valid stock price update
                if (data.symbol && data.price !== undefined) {
                    setLivePrices(prevPrices => ({
                        ...prevPrices,
                        [data.symbol]: data.price
                    }));
                }
            } catch (err) {
                console.error('Error parsing WebSocket message:', err);
            }
        }
    }, [latestStockPriceMessage]);

    // RENDER
    return (
        <div className="watchlist-container">
            <h2>My Watchlist</h2>

            <form onSubmit={handleAddStock}>
                <input
                    type="text"
                    value={newStockSymbol}
                    onChange={e => setNewStockSymbol(e.target.value.toUpperCase())}
                    placeholder="Add stock symbol (e.g., AAPL)"
                    disabled={loading}
                />
                <button type="submit" disabled={loading || !newStockSymbol.trim()}>
                    Add Stock
                </button>
            </form>

            {error && <p style={{ color: 'red' }}>Error: {error}</p>}

            <div className="watchlist-body">
                {loading && watchlist.length === 0 ? (
                    <p>Loading watchlist...</p>
                ) : !loading && !error && watchlist.length === 0 ? (
                    <p>Your watchlist is empty. Add some stocks!</p>
                ) : watchlist.length > 0 ? (
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Current Price</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {watchlist.map(item => (
                                <tr key={item.symbol}>
                                    <td>{item.symbol}</td>
                                    <td>
                                        {livePrices[item.symbol] 
                                            ? `$${livePrices[item.symbol].toFixed(2)}` 
                                            : 'Loading...'}
                                    </td>
                                    <td>
                                        <button onClick={() => handleRemoveStock(item.symbol)} disabled={loading}>
                                            Remove
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                ) : null}
            </div>
        </div>
    );
};

export default Watchlist;

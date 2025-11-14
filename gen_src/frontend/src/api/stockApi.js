import axios from 'axios';

// Create an axios instance with a base URL for the backend API.
// This makes requests cleaner and easier to manage across the application.
// The backend is expected to be running on port 8000 during development.
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Fetches the list of most active stocks from the backend API.
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of active stock objects.
 * @throws {Error} Throws an error if the API call fails, to be handled by the caller.
 */
export const getActiveStocks = async () => {
  try {
    // Make a GET request to the /stocks/active endpoint
    const response = await apiClient.get('/stocks/active');
    // Return the data from the response body
    return response.data;
  } catch (error) {
    // Log the error for debugging purposes
    console.error('Failed to fetch active stocks:', error);
    // Re-throw the error so that the calling component (e.g., a React hook or component)
    // can catch it and update the UI state accordingly (e.g., show an error message).
    throw error;
  }
};

/**
 * Fetches the daily historical data for a specific stock symbol.
 * @param {string} symbol - The stock symbol (e.g., 'RY').
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of historical data points.
 * @throws {Error} Throws an error if the API call fails, to be handled by the caller.
 */
export const getHistoricalStockData = async (symbol) => {
  try {
    // Define the API endpoint URL, incorporating the stock symbol
    const endpoint = `/stocks/${symbol}/historical`;
    // Make a GET request to the historical data endpoint
    const response = await apiClient.get(endpoint);
    // Return the data from the response body
    return response.data;
  } catch (error) {
    // Log the error for debugging purposes
    console.error(`Failed to fetch historical stock data for ${symbol}:`, error);
    // Re-throw the error for the calling component to handle.
    throw error;
  }
};

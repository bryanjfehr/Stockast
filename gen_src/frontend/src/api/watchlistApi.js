/**
 * @file This file contains functions for managing a user's stock watchlist via authenticated API calls.
 * It uses axios to communicate with the backend service.
 */

import axios from 'axios';

const API_URL = '/api/v1/watchlist';

/**
 * Fetches the user's watchlist from the server.
 * @param {string} token - The user's authentication token (JWT).
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of watchlist items.
 * @throws {Error} Throws an error if the API call fails.
 */
export const getWatchlist = async (token) => {
  try {
    const response = await axios.get(`${API_URL}/`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch watchlist:', error.response ? error.response.data : error.message);
    throw error;
  }
};

/**
 * Adds a stock to the user's watchlist.
 * @param {string} symbol - The stock symbol to add.
 * @param {string} token - The user's authentication token (JWT).
 * @returns {Promise<Object>} A promise that resolves to the newly added watchlist item.
 * @throws {Error} Throws an error if the API call fails.
 */
export const addStockToWatchlist = async (symbol, token) => {
  try {
    const response = await axios.post(
      `${API_URL}/`,
      { symbol },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to add stock to watchlist:', error.response ? error.response.data : error.message);
    throw error;
  }
};

/**
 * Removes a stock from the user's watchlist.
 * @param {string} symbol - The stock symbol to remove.
 * @param {string} token - The user's authentication token (JWT).
 * @returns {Promise<Object>} A promise that resolves to a success message from the API.
 * @throws {Error} Throws an error if the API call fails.
 */
export const removeStockFromWatchlist = async (symbol, token) => {
  try {
    const response = await axios.delete(`${API_URL}/${symbol}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to remove stock from watchlist:', error.response ? error.response.data : error.message);
    throw error;
  }
};

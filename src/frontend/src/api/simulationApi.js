/**
 * @file This file contains functions for interacting with the trading simulation API endpoints.
 * It provides methods to start a simulation, get its status, and retrieve its history.
 */

import axios from 'axios';

// Create an axios instance with a base URL for the API.
// This makes it easier to manage API endpoints and can be configured
// with environment variables in a real-world application.
const apiClient = axios.create({
  baseURL: '/api/v1',
});

/**
 * Sends a POST request to begin a new trading simulation.
 * @param {number} initialCapital - The starting capital for the simulation.
 * @param {string} token - The user's authentication token.
 * @returns {Promise<object>} A promise that resolves to the newly started simulation's status.
 * @throws {Error} Throws an error if the API call fails.
 */
export const startSimulation = async (initialCapital, token) => {
  try {
    const response = await apiClient.post(
      '/simulation/start',
      { initial_capital: initialCapital },
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to start simulation:', error.response ? error.response.data : error.message);
    throw error;
  }
};

/**
 * Sends a GET request to get the active simulation's performance and status.
 * @param {string} token - The user's authentication token.
 * @returns {Promise<object>} A promise that resolves to the simulation status object.
 * @throws {Error} Throws an error if the API call fails.
 */
export const getSimulationStatus = async (token) => {
  try {
    const response = await apiClient.get('/simulation/status', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to get simulation status:', error.response ? error.response.data : error.message);
    throw error;
  }
};

/**
 * Sends a GET request to retrieve the trade history for the active simulation.
 * @param {string} token - The user's authentication token.
 * @returns {Promise<Array<object>>} A promise that resolves to an array of trade history objects.
 * @throws {Error} Throws an error if the API call fails.
 */
export const getSimulationHistory = async (token) => {
  try {
    const response = await apiClient.get('/simulation/history', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to get simulation history:', error.response ? error.response.data : error.message);
    throw error;
  }
};

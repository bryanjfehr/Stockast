import axios from 'axios';

/**
 * @file This file contains functions for updating user-specific settings via authenticated API calls.
 */

// It's a good practice to have a base URL for your API, which can be configured via environment variables.
// For this example, we'll assume the API is served from the same origin.
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '';

/**
 * Sends a PUT request to update user settings like the Vertex AI API key.
 *
 * @param {object} settingsData - An object containing the settings to update (e.g., { vertex_ai_api_key: '...' }).
 * @param {string} token - The user's JWT for authentication.
 * @returns {Promise<object>} A promise that resolves with the response data from the server (e.g., a success message or updated user object).
 * @throws {Error} Throws an error if the API call fails, which can be caught by the calling function.
 */
export const updateSettings = async (settingsData, token) => {
  try {
    const endpoint = `${API_BASE_URL}/api/v1/settings/`;

    const response = await axios.put(endpoint, settingsData, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    return response.data;
  } catch (error) {
    // Log a more informative error message if available from the server response
    const errorMessage = error.response?.data?.detail || error.message || 'An unknown error occurred.';
    console.error('Failed to update settings:', errorMessage);

    // Re-throw the error so it can be handled by the calling component or hook.
    // It's often useful to throw the original error object to preserve stack trace and response details.
    throw error;
  }
};

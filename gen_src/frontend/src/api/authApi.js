/**
 * This file contains functions for making API calls related to user authentication.
 */

import axios from 'axios';

// A base URL for the API can be centralized in a config file.
const API_BASE_URL = '/api/v1';

/**
 * Sends a POST request to authenticate the user and retrieve a JWT.
 * FastAPI's OAuth2PasswordRequestForm expects 'application/x-www-form-urlencoded' data.
 * 
 * @param {string} email - The user's email address.
 * @param {string} password - The user's password.
 * @returns {Promise<object>} A promise that resolves with the response data (e.g., { access_token, token_type }).
 * @throws {Error} Throws an error if the login request fails, allowing the caller to handle it.
 */
export const login = async (email, password) => {
  try {
    const loginUrl = `${API_BASE_URL}/users/login`;

    // Prepare the request body as `URLSearchParams` for the required content type.
    const formData = new URLSearchParams();
    formData.append('username', email); // The form field is 'username' for OAuth2PasswordRequestForm
    formData.append('password', password);

    const response = await axios.post(loginUrl, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    return response.data;
  } catch (error) {
    console.error('Login failed:', error.response ? error.response.data : error.message);
    // Re-throw the error to be handled by the calling component or hook.
    throw error;
  }
};

/**
 * Sends a POST request to create a new user account.
 * 
 * @param {string} email - The new user's email address.
 * @param {string} password - The new user's password.
 * @returns {Promise<object>} A promise that resolves with the new user's details (e.g., id, email).
 * @throws {Error} Throws an error if the registration request fails, allowing the caller to handle it.
 */
export const register = async (email, password) => {
  try {
    const registerUrl = `${API_BASE_URL}/users/register`;
    const requestBody = { email, password };

    // axios defaults to 'application/json' for object bodies, which is what we want here.
    const response = await axios.post(registerUrl, requestBody);

    return response.data;
  } catch (error) {
    console.error('Registration failed:', error.response ? error.response.data : error.message);
    // Re-throw the error to be handled by the calling component or hook.
    throw error;
  }
};

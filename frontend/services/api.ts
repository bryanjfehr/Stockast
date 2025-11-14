/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import axios from 'axios';
import * as Keychain from 'react-native-keychain';

// Define your backend API base URL
const API_BASE_URL = 'http://localhost:3000/api'; // Adjust as per your backend setup
const KEYCHAIN_SERVICE_API_KEYS = 'stockastApiKeys';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000, // 10 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach API keys from Keychain
api.interceptors.request.use(
  async (config) => {
    try {
      const credentials = await Keychain.getGenericPassword({
        service: KEYCHAIN_SERVICE_API_KEYS,
      });
      if (credentials) {
        // Assuming your backend expects these headers
        config.headers['X-Exchange-Api-Key'] = credentials.username;
        config.headers['X-Exchange-Api-Secret'] = credentials.password;
      }
    } catch (error) {
      console.error('Failed to retrieve API keys from Keychain:', error);
      // Optionally, handle this by redirecting to login or showing an error
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);
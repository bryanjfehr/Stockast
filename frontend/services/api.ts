/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import axios from 'axios';
import SInfo from 'react-native-sensitive-info';

// Define your backend API base URL
const API_BASE_URL = 'http://localhost:3000/api'; // Adjust as per your backend setup
const API_KEYS_STORAGE_KEY = 'stockastApiKeys';

// Define options for react-native-sensitive-info.
// This ensures consistency across your app.
const SENSITIVE_INFO_OPTIONS = {
  sharedPreferencesName: 'mySharedPrefs', // Recommended for Android
  keychainService: 'myKeychain', // Recommended for iOS
};

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
      const credentialsJson = await SInfo.getItem(API_KEYS_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);
      if (credentialsJson) {
        // We assume the credentials are a JSON string with username (API Key) and password (API Secret)
        const credentials = JSON.parse(credentialsJson);
        // Assuming your backend expects these headers
        config.headers['X-Exchange-Api-Key'] = credentials.username;
        config.headers['X-Exchange-Api-Secret'] = credentials.password;
        config.headers['X-Santiment-Api-Key'] = credentials.santiment;
      }
    } catch (error) {
      console.error('Failed to retrieve API keys from secure storage:', error);
      // Optionally, handle this by redirecting to login or showing an error
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);
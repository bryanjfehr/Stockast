/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import axios from 'axios';
import SInfo from 'react-native-sensitive-info';

const API_URL = 'http://127.0.0.1:3000/api'; // Use 10.0.2.2 for Android emulator if connecting to localhost

export const api = axios.create({
  baseURL: API_URL,
  timeout: 10000, // 10 second timeout
});

// Define constants for storage keys
const API_KEYS_STORAGE_KEY = 'stockastApiKeys';
const SENSITIVE_INFO_OPTIONS = {
  sharedPreferencesName: 'mySharedPrefs',
  keychainService: 'myKeychain',
};

// Use an interceptor to dynamically add API keys to headers
api.interceptors.request.use(
  async (config) => {
    const apiKeysJson = await SInfo.getItem(API_KEYS_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);

    if (apiKeysJson) {
      const apiKeys = JSON.parse(apiKeysJson);
      config.headers['X-Exchange-Api-Key'] = apiKeys.exchangeApiKey;
      config.headers['X-Exchange-Api-Secret'] = apiKeys.exchangeApiSecret;
      config.headers['X-Santiment-Api-Key'] = apiKeys.santimentApiKey;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
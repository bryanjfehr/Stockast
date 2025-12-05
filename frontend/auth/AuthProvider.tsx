/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, {
  createContext,
  useState,
  useEffect,
  useContext,
  useCallback,
} from 'react';
import SInfo from 'react-native-sensitive-info';
import { api } from '../services/api';

// Define the structure for the API keys object
interface ApiKeys {
  exchange_api_key: string;
  exchange_api_secret: string;
  santiment_api_key: string;
}

interface AuthContextType {
  hasKeys: boolean;
  isPinAuthenticated: boolean;
  isLoading: boolean;
  setApiKeys: (keys: ApiKeys) => Promise<boolean>;
  setIsLoading: (loading: boolean) => void;
  checkAuthStatus: () => Promise<void>;
  clearAuth: () => Promise<void>;
}

// Create the AuthContext
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * AuthProvider component to manage authentication state and provide it to children.
 * It handles storing/retrieving API keys and PIN securely.
 */
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [hasKeys, setHasKeys] = useState<boolean>(false);
  const [isPinAuthenticated, setIsPinAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const API_KEYS_STORAGE_KEY = 'stockastApiKeys';

  const SENSITIVE_INFO_OPTIONS = {
    sharedPreferencesName: 'mySharedPrefs', // Recommended for Android
    keychainService: 'myKeychain', // Recommended for iOS
  };

  // Function to check initial authentication state
  const checkAuthStatus = useCallback(async () => {
    try {
      setIsLoading(true);

      const apiKeysJson = await SInfo.getItem(API_KEYS_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);
      const keysExist = !!apiKeysJson;
      setHasKeys(keysExist);
      
      // --- PIN BYPASS ---
      // If keys exist, we consider the user authenticated and bypass the PIN screen.
      setIsPinAuthenticated(keysExist);
    } catch (error) {
      console.error('Failed to check auth status:', error);
      setHasKeys(false);
      setIsPinAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  // Function to set API keys
  const setApiKeys = useCallback(async (keys: ApiKeys): Promise<boolean> => {
    try {
      // The interceptor needs the keys in camelCase format.
      const keysToStore = {
        exchangeApiKey: keys.exchange_api_key,
        exchangeApiSecret: keys.exchange_api_secret,
        santimentApiKey: keys.santiment_api_key,
      };
      await SInfo.setItem(API_KEYS_STORAGE_KEY, JSON.stringify(keysToStore), SENSITIVE_INFO_OPTIONS);
      return true;
    } catch (error) {
      return false;
    }
  }, []);

  // Function to clear all authentication data
  const clearAuth = useCallback(async () => {
    try {
      await SInfo.deleteItem(API_KEYS_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);
      await checkAuthStatus(); // Re-check status to reset hasKeys/hasPinSet correctly
      // Reset all auth states
      setHasKeys(false);
      setIsPinAuthenticated(false);
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }, []); // No dependencies needed for clearAuth as it resets local state

  const value = {
    hasKeys,
    isPinAuthenticated,
    isLoading,
    setApiKeys,
    setIsLoading,
    checkAuthStatus,
    clearAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * Custom hook to use the AuthContext.
 * Throws an error if used outside of an AuthProvider.
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
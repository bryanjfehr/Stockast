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
import AsyncStorage from '@react-native-async-storage/async-storage'; // Using the community package

// Define types for API keys and PIN
interface ApiKeys {
  exchangeApiKey: string;
  exchangeApiSecret: string;
  santimentApiKey: string;
}

interface AuthContextType {
  hasKeys: boolean;
  isPinAuthenticated: boolean;
  isLoading: boolean;
  setApiKeys: (keys: ApiKeys) => Promise<boolean>;
  setPin: (pin: string) => Promise<boolean>;
  authenticatePin: (pin: string) => Promise<boolean>;
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

  // Constants for storage keys
  const API_KEYS_STORAGE_KEY = 'stockastApiKeys';
  const PIN_STORAGE_KEY = 'stockastPin';
  const ASYNC_STORAGE_HAS_PIN = 'stockastHasPin';

  // Define options for react-native-sensitive-info.
  const SENSITIVE_INFO_OPTIONS = {
    sharedPreferencesName: 'mySharedPrefs', // Recommended for Android
    keychainService: 'myKeychain', // Recommended for iOS
  };

  // Function to check initial authentication state
  const checkAuthStatus = useCallback(async () => {
    try {
      setIsLoading(true);

      // Check for API keys
      const apiKeysJson = await SInfo.getItem(API_KEYS_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);
      const keysExist = !!apiKeysJson;
      setHasKeys(keysExist);

      // Check if a PIN is set (AsyncStorage is used to quickly check existence without retrieving)
      const pinSet = await AsyncStorage.getItem(ASYNC_STORAGE_HAS_PIN);

      // If keys exist and a PIN is set, but not yet authenticated, then PIN is needed.
      // Otherwise, if no PIN is set, or no keys, no PIN authentication is needed yet.
      if (keysExist && pinSet) {
        setIsPinAuthenticated(false); // PIN is set, but not yet authenticated for this session
      } else {
        setIsPinAuthenticated(true); // No PIN set, or no keys, so no PIN auth needed yet
      }
    } catch (error) {
      console.error('Failed to check auth status:', error);
      // Decide how to handle this error: maybe clear everything or show an error screen
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
      // Store as a JSON string, matching the structure api.ts expects
      const credentialsToStore = JSON.stringify({
        username: keys.exchangeApiKey,
        password: keys.exchangeApiSecret,
        santiment: keys.santimentApiKey,
      });

      await SInfo.setItem(API_KEYS_STORAGE_KEY, credentialsToStore, SENSITIVE_INFO_OPTIONS);

      setHasKeys(true);
      // After setting keys, if a PIN is already set, we need to authenticate it.
      const pinSet = await AsyncStorage.getItem(ASYNC_STORAGE_HAS_PIN);
      if (pinSet) {
        setIsPinAuthenticated(false);
      } else {
        setIsPinAuthenticated(true); // No PIN set, so consider authenticated for now
      }
      return true;
    } catch (error) {
      console.error('Failed to set API keys:', error);
      return false;
    }
  }, []);

  // Function to set a new PIN
  const setPin = useCallback(async (pin: string): Promise<boolean> => {
    try {
      await SInfo.setItem(PIN_STORAGE_KEY, pin, SENSITIVE_INFO_OPTIONS);
      await AsyncStorage.setItem(ASYNC_STORAGE_HAS_PIN, 'true');
      setIsPinAuthenticated(true);
      return true;
    } catch (error) {
      console.error('Failed to set PIN:', error);
      return false;
    }
  }, []);

  // Function to authenticate with an existing PIN
  const authenticatePin = useCallback(async (pin: string): Promise<boolean> => {
    try {
      const storedPin = await SInfo.getItem(PIN_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);
      if (storedPin && storedPin === pin) {
        setIsPinAuthenticated(true);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to authenticate PIN:', error);
      return false;
    }
  }, []);

  // Function to clear all authentication data
  const clearAuth = useCallback(async () => {
    try {
      await SInfo.deleteItem(API_KEYS_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);
      await SInfo.deleteItem(PIN_STORAGE_KEY, SENSITIVE_INFO_OPTIONS);
      await AsyncStorage.removeItem(ASYNC_STORAGE_HAS_PIN);
      setHasKeys(false);
      setIsPinAuthenticated(false);
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }, []);

  const value = {
    hasKeys,
    isPinAuthenticated,
    isLoading,
    setApiKeys,
    setPin,
    authenticatePin,
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
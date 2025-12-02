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
import { api } from '../services/api';

// Define the structure for the API keys object
interface ApiKeys {
  exchange_api_key: string;
  exchange_api_secret: string;
  santiment_api_key: string;
}

interface AuthContextType {
  hasKeys: boolean;
  hasPinSet: boolean;
  isPinAuthenticated: boolean;
  isLoading: boolean;
  setApiKeys: (keys: ApiKeys) => Promise<boolean>;
  setPin: (pin: string) => Promise<boolean>;
  setIsLoading: (loading: boolean) => void;
  setHasPinSet: (hasPinSet: boolean) => void;
  checkAuthStatus: () => Promise<void>;
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
  const [hasPinSet, setHasPinSet] = useState<boolean>(false); // New state to track if a PIN has been set
  const [isPinAuthenticated, setIsPinAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const API_KEYS_STORAGE_KEY = 'stockastApiKeys';
  const PIN_STORAGE_KEY = 'stockastPin';
  const ASYNC_STORAGE_HAS_PIN = 'stockastHasPin';

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

      const pinSetInStorage = await AsyncStorage.getItem(ASYNC_STORAGE_HAS_PIN);
      setHasPinSet(!!pinSetInStorage); // Update new state

      // On startup, if keys exist and a PIN is set, the user is NOT yet authenticated for the session.
      // If keys don't exist, or no PIN is set, then PIN authentication isn't the current step.
      // The AppNavigator will handle showing KeyInput or PINAuth based on hasKeys and hasPinSet.
      // isPinAuthenticated should only be true AFTER successful PIN entry.
      if (keysExist && pinSetInStorage) {
        setIsPinAuthenticated(false);
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

  // Function to set a new PIN
  const setPin = useCallback(async (pin: string): Promise<boolean> => {
    try {
      await SInfo.setItem(PIN_STORAGE_KEY, pin, SENSITIVE_INFO_OPTIONS);
      await AsyncStorage.setItem(ASYNC_STORAGE_HAS_PIN, 'true');
      setIsPinAuthenticated(true); // Successfully set a new PIN, so user is authenticated
      setHasPinSet(true);
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
      // Ensure storedPin is not null/undefined before comparing.
      // SInfo.getItem can return null if the key doesn't exist.
      // If storedPin is null/undefined, it means no PIN was set, so it's an incorrect PIN.
      if (storedPin !== null && storedPin !== undefined && storedPin === pin) {
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
      // Reset all auth states
      setHasKeys(false);
      setHasPinSet(false);
      setIsPinAuthenticated(false);
    } catch (error) {
      console.error('Failed to clear auth data:', error);
    }
  }, []); // No dependencies needed for clearAuth as it resets local state

  const value = {
    hasKeys,
    hasPinSet,
    isPinAuthenticated,
    isLoading,
    setApiKeys,
    setPin,
    setIsLoading,
    setHasPinSet,
    checkAuthStatus,
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
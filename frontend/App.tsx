/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

// This import must be at the top of the file to initialize gesture handler
import { Alert } from 'react-native';
import React,
  { useEffect } from 'react';
import {
  SafeAreaView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  ActivityIndicator,
} from 'react-native';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';

import { AuthProvider, useAuth } from './auth/AuthProvider';
import { api } from './services/api';

import HomeScreen from './screens/HomeScreen';
import KeyInputScreen from './screens/KeyInputScreen';
import { useAppState } from './hooks/useAppState';
import { useBackgroundFetch } from './hooks/useBackgroundFetch';

// Define the type for the navigation stack parameters
type RootStackParamList = {
  KeyInput: undefined;
  Home: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

/**
 * The main navigation logic of the app.
 * It determines which screen to show based on the authentication state.
 */
const AppNavigator: React.FC = () => {
  const { hasKeys, isPinAuthenticated, isLoading } = useAuth();

  // Perform initial calibration check if keys are set
  useEffect(() => {
    if (hasKeys && isPinAuthenticated) {
      const calibrateBot = async () => {
        try {
          console.log('Performing initial calibration...');
          await api.post('/calibrate'); // This validates the keys on the backend.
          console.log('API Key calibration successful.');
        } catch (error: any) {
          console.error('API Key calibration failed:', error.response?.data?.detail || error.message);
          // Notify the user that their exchange API keys are invalid.
          Alert.alert('Calibration Failed', `Could not validate API keys. Please check them and restart the app. \n\nError: ${error.response?.data?.detail || error.message}`);
        }
      };
      calibrateBot();
    }
  }, [hasKeys, isPinAuthenticated]);

  if (isLoading) {
    return (
      <View style={styles.loaderContainer}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!hasKeys ? ( // If no keys, go to KeyInputScreen
          <Stack.Screen name="KeyInput" component={KeyInputScreen} />
        ) : ( // If keys exist, PIN is bypassed, go to Home
          <Stack.Screen name="Home" component={HomeScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};

/**
 * Root component of the application.
 * Sets up providers, background tasks, and state listeners.
 */
const App: React.FC = () => {
  // Use the custom hooks to handle side effects.
  // This keeps the App component clean and focused on rendering.
  useAppState();
  useBackgroundFetch();

  // The GestureHandlerRootView is removed as it's part of a dependency
  // we are removing to fix build errors.
  // SafeAreaView is now the root component.
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <AuthProvider>
        <AppNavigator />
      </AuthProvider>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212', // Dark theme for the root container
  },
  loaderContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#121212',
  },
});

export default App;
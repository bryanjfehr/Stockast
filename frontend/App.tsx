/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React,
  { useEffect } from 'react';
import {
  SafeAreaView,
  StatusBar,
  StyleSheet,
  View,
  ActivityIndicator,
} from 'react-native';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';

import { AuthProvider, useAuth } from './auth/AuthProvider';
import { api } from './services/api';

import HomeScreen from './screens/HomeScreen';
import KeyInputScreen from './screens/KeyInputScreen';
import PINAuthScreen from './screens/PINAuthScreen';
import { useAppState } from './hooks/useAppState';
import { useBackgroundFetch } from './hooks/useBackgroundFetch';

// Define the type for the navigation stack parameters
type RootStackParamList = {
  KeyInput: undefined;
  PINAuth: undefined;
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
          await api.post('/calibrate');
          console.log('Calibration successful.');
        } catch (error) {
          console.error('Calibration failed:', error);
          // Optionally, notify the user of the calibration failure
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
        {!hasKeys ? (
          <Stack.Screen name="KeyInput" component={KeyInputScreen} />
        ) : !isPinAuthenticated ? (
          <Stack.Screen name="PINAuth" component={PINAuthScreen} />
        ) : (
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
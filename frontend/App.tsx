/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React,
  {
    useEffect,
    useContext,
    useState
  } from 'react';
import {
  AppState,
  Platform,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  View,
  ActivityIndicator,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import BackgroundFetch from 'react-native-background-fetch';

import { AuthProvider, useAuth } from './auth/AuthProvider';
import { api } from './services/api';

import HomeScreen from './screens/HomeScreen';
import KeyInputScreen from './screens/KeyInputScreen';
import PINAuthScreen from './screens/PINAuthScreen';

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
  useEffect(() => {
    // --- AppState Listener for backgrounding ---
    const handleAppStateChange = (nextAppState: string) => {
      if (nextAppState === 'background') {
        console.log('App has gone to the background. Running strategies...');
        // This is a fire-and-forget task when the app is minimized.
        api.post('/run-strategies').catch(error => {
          console.error('Failed to run strategies on backgrounding:', error);
        });
      }

      // Placeholder for Windows-specific tray minimization logic
      if (Platform.OS === 'windows' && nextAppState === 'background') {
        console.log('App backgrounded on Windows. Implement tray logic here.');
        // e.g., NativeModules.WindowControl.minimizeToTray();
      }
    };

    const appStateSubscription = AppState.addEventListener(
      'change',
      handleAppStateChange,
    );

    // --- BackgroundFetch Configuration ---
    const initBackgroundFetch = async () => {
      try {
        const status = await BackgroundFetch.configure(
          {
            minimumFetchInterval: 5, // <-- minutes
            stopOnTerminate: false,
            startOnBoot: true,
            enableHeadless: true, // <-- Required for background tasks after app termination
            requiresCharging: false,
            requiredNetworkType: BackgroundFetch.NETWORK_TYPE_ANY,
          },
          async (taskId: string) => {
            console.log('[BackgroundFetch] Task received:', taskId);

            try {
              // Fetch sentiment data
              const response = await api.get('/sentiment');
              console.log('[BackgroundFetch] Sentiment fetched:', response.data);
            } catch (error) {
              console.error('[BackgroundFetch] API call failed:', error);
            }

            // Inform the OS that the task is complete
            BackgroundFetch.finish(taskId);
          },
          (taskId: string) => {
            // This is called when a task timeout occurs.
            console.warn('[BackgroundFetch] Task timed out:', taskId);
            BackgroundFetch.finish(taskId);
          },
        );

        console.log('[BackgroundFetch] configure status:', status);
      } catch (e) {
        console.error('[BackgroundFetch] configure failed:', e);
      }
    };

    initBackgroundFetch();

    // Cleanup function
    return () => {
      appStateSubscription.remove();
    };
  }, []);

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

// --- Headless Task for BackgroundFetch ---
// This function will be executed when the app is terminated.
const headlessTask = async (event: { taskId: string; timeout: boolean }) => {
  const { taskId } = event;
  console.log('[BackgroundFetch Headless] Task:', taskId);

  try {
    const response = await api.get('/sentiment');
    console.log('[BackgroundFetch Headless] Sentiment fetched:', response.data);
  } catch (error) {
    console.error('[BackgroundFetch Headless] API call failed:', error);
  }

  BackgroundFetch.finish(taskId);
};

BackgroundFetch.registerHeadlessTask(headlessTask);
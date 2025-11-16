import {useEffect} from 'react';
import {AppState, Platform, NativeModules} from 'react-native';
import {api} from '../services/api'; // Assuming you have an API service at this path

export const useAppState = () => {
  useEffect(() => {
    const handleAppStateChange = (nextAppState: string) => {
      if (nextAppState === 'background') {
        if (Platform.OS === 'windows') {
          // On Windows, you might want to minimize to the system tray
          // instead of running a background task.
          console.log('App backgrounded on Windows. Implement tray logic here.');
          // Example: NativeModules.WindowControl?.minimizeToTray();
        } else {
          // This logic is specific to mobile platforms.
          console.log('App has gone to the background. Running strategies...');
          api.post('/run-strategies').catch(error => {
            console.error('Failed to run strategies on backgrounding:', error);
          });
        }
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);

    return () => {
      subscription.remove();
    };
  }, []);
};
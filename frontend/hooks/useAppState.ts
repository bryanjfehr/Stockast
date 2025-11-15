import {useEffect} from 'react';
import {AppState} from 'react-native';
import {api} from '../services/api'; // Assuming you have an API service at this path

export const useAppState = () => {
  useEffect(() => {
    const handleAppStateChange = (nextAppState: string) => {
      if (nextAppState === 'background') {
        console.log('App has gone to the background. Running strategies...');
        // Example: Trigger an API call when the app goes to the background
        api.post('/run-strategies').catch(error => {
          console.error('Failed to run strategies on backgrounding:', error);
        });
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);

    return () => {
      subscription.remove();
    };
  }, []);
};
import {useEffect} from 'react';
import BackgroundFetch from 'react-native-background-fetch';

export const useBackgroundFetch = () => {
  useEffect(() => {
    const initBackgroundFetch = async () => {
      const onEvent = async (taskId: string) => {
        console.log('[BackgroundFetch] task: ', taskId);
        // Your background task logic here
        BackgroundFetch.finish(taskId);
      };

      const onTimeout = async (taskId: string) => {
        console.warn('[BackgroundFetch] TIMEOUT task: ', taskId);
        BackgroundFetch.finish(taskId);
      };

      await BackgroundFetch.configure(
        {
          minimumFetchInterval: 15, // Minutes
          stopOnTerminate: false,
          enableHeadless: true,
          startOnBoot: true,
        },
        onEvent,
        onTimeout,
      );
    };

    initBackgroundFetch();
  }, []);
};
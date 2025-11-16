/**
 * @format
 */

import {AppRegistry} from 'react-native';
import BackgroundFetch from 'react-native-background-fetch';
import App from './App';
import {name as appName} from './app.json';
import {api} from './services/api';

/**
 * --- Headless Task Registration ---
 * This task will be called by the OS when the app is in the background or terminated.
 */
const headlessTask = async (event: {taskId: string}) => {
  console.log('[BackgroundFetch HeadlessTask] start', event.taskId);

  // Perform your background task here, e.g., run strategies
  await api.post('/run-strategies');

  // Signal to the OS that the task is complete.
  BackgroundFetch.finish(event.taskId);
};

BackgroundFetch.registerHeadlessTask(headlessTask);

AppRegistry.registerComponent(appName, () => App);
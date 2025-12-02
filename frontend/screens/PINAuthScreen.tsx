/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  Button,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { StackScreenProps } from '@react-navigation/stack';
import { useAuth } from '../auth/AuthProvider';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Define the RootStackParamList type (should match App.tsx)
type RootStackParamList = {
  KeyInput: undefined;
  PINAuth: undefined;
  Home: undefined;
};

type PINAuthScreenProps = StackScreenProps<RootStackParamList, 'PINAuth'>;

const PINAuthScreen: React.FC<PINAuthScreenProps> = ({ navigation }) => {
  const { setPin, authenticatePin, isLoading, setIsLoading } = useAuth();
  const [pin, setPinValue] = useState<string>('');
  const [isSettingNewPin, setIsSettingNewPin] = useState<boolean>(false);

  useEffect(() => {
    const checkPinExistence = async () => {
      const hasPin = await AsyncStorage.getItem('stockastHasPin');
      setIsSettingNewPin(!hasPin);
    };
    checkPinExistence();
  }, []);

  const handlePinAction = async () => {
    if (!pin) {
      Alert.alert('Error', 'Please enter a PIN.');
      return;
    }

    setIsLoading(true);
    if (isSettingNewPin) {
      const success = await setPin(pin);
      if (success) {
        // AuthProvider will update isPinAuthenticated to true, triggering navigation to Home
      } else {
        Alert.alert('Error', 'Failed to set PIN. Please try again.');
      }
    } else {
      const success = await authenticatePin(pin);
      if (success) {
        Alert.alert('Success', 'PIN authenticated!');
        // AuthProvider will update isPinAuthenticated to true, triggering navigation to Home
      } else {
        Alert.alert('Error', 'Incorrect PIN. Please try again.');
      }
    }
    setIsLoading(false);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>
          {isSettingNewPin ? 'Set Your PIN' : 'Enter Your PIN'}
        </Text>
        <TextInput
          style={styles.input}
          placeholder="PIN"
          placeholderTextColor="#888"
          value={pin}
          onChangeText={setPinValue}
          keyboardType="numeric"
          secureTextEntry
          maxLength={6} // Common PIN length
        />
        <Button
          title={isSettingNewPin ? 'Set PIN' : 'Authenticate'}
          onPress={handlePinAction}
          disabled={isLoading}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  scrollContent: { flexGrow: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 24, marginBottom: 30, color: '#fff' },
  input: { width: '80%', padding: 10, marginVertical: 10, borderWidth: 1, borderColor: '#555', borderRadius: 5, color: '#fff', backgroundColor: '#333', textAlign: 'center' },
});

export default PINAuthScreen;
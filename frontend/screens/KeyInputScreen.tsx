/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useState } from 'react';
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

// Define the RootStackParamList type (should match App.tsx)
type RootStackParamList = {
  KeyInput: undefined;
  PINAuth: undefined;
  Home: undefined;
};

type KeyInputScreenProps = StackScreenProps<RootStackParamList, 'KeyInput'>;

const KeyInputScreen: React.FC<KeyInputScreenProps> = ({ navigation }) => {
  const { setApiKeys, isLoading } = useAuth();
  const [apiKey, setApiKey] = useState<string>('');
  const [apiSecret, setApiSecret] = useState<string>('');

  const handleSaveKeys = async () => {
    if (!apiKey || !apiSecret) {
      Alert.alert('Error', 'Please enter both API Key and API Secret.');
      return;
    }

    const success = await setApiKeys({
      exchangeApiKey: apiKey,
      exchangeApiSecret: apiSecret,
    });

    if (success) {
      Alert.alert('Success', 'API Keys saved securely!');
      // After saving keys, the AuthProvider will update its state.
      // The AppNavigator will then automatically navigate to PINAuth or Home.
    } else {
      Alert.alert('Error', 'Failed to save API Keys. Please try again.');
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>Enter Your Exchange API Keys</Text>
        <TextInput
          style={styles.input}
          placeholder="API Key"
          placeholderTextColor="#888"
          value={apiKey}
          onChangeText={setApiKey}
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="API Secret"
          placeholderTextColor="#888"
          value={apiSecret}
          onChangeText={setApiSecret}
          secureTextEntry
          autoCapitalize="none"
        />
        <Button title="Save Keys" onPress={handleSaveKeys} disabled={isLoading} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  scrollContent: { flexGrow: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 24, marginBottom: 30, color: '#fff' },
  input: { width: '80%', padding: 10, marginVertical: 10, borderWidth: 1, borderColor: '#555', borderRadius: 5, color: '#fff', backgroundColor: '#333' },
});

export default KeyInputScreen;
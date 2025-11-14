/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React from 'react';
import { View, Text, Button, StyleSheet, Alert } from 'react-native';
import { StackScreenProps } from '@react-navigation/stack';
import { useAuth } from '../auth/AuthProvider';

// Define the RootStackParamList type (should match App.tsx)
type RootStackParamList = {
  KeyInput: undefined;
  PINAuth: undefined;
  Home: undefined;
};

type HomeScreenProps = StackScreenProps<RootStackParamList, 'Home'>;

const HomeScreen: React.FC<HomeScreenProps> = () => {
  const { clearAuth } = useAuth();

  const handleLogout = async () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to log out and clear all stored credentials?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Logout', onPress: async () => await clearAuth() },
      ],
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Welcome to Stockast Bot!</Text>
      <Text style={styles.subtitle}>Your trading bot is active.</Text>
      <Button title="Logout" onPress={handleLogout} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#121212' },
  title: { fontSize: 28, fontWeight: 'bold', marginBottom: 20, color: '#fff' },
  subtitle: { fontSize: 18, marginBottom: 40, color: '#ccc' },
});

export default HomeScreen;
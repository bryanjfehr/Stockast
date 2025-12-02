/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, FlatList } from 'react-native';
import { api } from '../services/api';

interface Balance {
  asset: string;
  free: number;
}

const AccountBalance: React.FC = () => {
  const [balances, setBalances] = useState<Balance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBalance = async () => {
      try {
        console.log('[AccountBalance] Fetching balances...');
        setLoading(true);
        const response = await api.get('/account/balance');
        console.log('[AccountBalance] Raw data received:', response.data);
        // Add validation to ensure the response is an array before setting state
        if (Array.isArray(response.data)) {
          setBalances(response.data);
          setError(null);
        } else {
          throw new Error('Received invalid data format for balances.');
        }
      } catch (err: any) {
        const errorMessage = err.message || 'Failed to fetch balances.';
        setError(errorMessage);
        console.error('[AccountBalance] Fetch error:', err.response ? err.response.data : err);
      } finally {
        setLoading(false);
        console.log('[AccountBalance] Fetch complete.');
      }
    };

    fetchBalance();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Account Balances</Text>
      {loading && <ActivityIndicator size="large" color="#fff" />}
      {error && <Text style={styles.errorText}>{error}</Text>}
      <FlatList
        // Add a message for when the list is empty but there's no error
        ListEmptyComponent={
          !loading && !error ? <Text style={styles.emptyText}>No assets found.</Text> : null
        }
        data={balances}
        keyExtractor={(item) => item.asset}
        renderItem={({ item }) => (
          <View style={styles.balanceRow}>
            <Text style={styles.assetText}>{item.asset}</Text>
            <Text style={styles.amountText}>{item.free.toFixed(8)}</Text>
          </View>
        )}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: 250,
    backgroundColor: '#1e1e1e',
    borderRadius: 8,
    marginRight: 5,
    padding: 10,
  },
  title: { color: '#fff', fontSize: 18, fontWeight: 'bold', marginBottom: 10, textAlign: 'center' },
  errorText: { color: 'red', textAlign: 'center' },
  balanceRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#333' },
  emptyText: { color: '#ccc', textAlign: 'center', fontStyle: 'italic', marginTop: 20 },
  assetText: { color: '#fff', fontSize: 16 },
  amountText: { color: '#ccc', fontSize: 16 },
});

export default AccountBalance;
/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, FlatList } from 'react-native';
import { api } from '../services/api';

interface TokenSentiment {
  net_sentiment: number;
  mention_growth_pct: number;
}

const HotTokens: React.FC = () => {
  const [tokens, setTokens] = useState<Record<string, TokenSentiment> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSentiment = async () => {
      try {
        setLoading(true);
        const response = await api.get('/sentiment');
        setTokens(response.data.top_sentiment);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch hot tokens.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchSentiment();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Hot Tokens</Text>
      {loading && <ActivityIndicator size="large" color="#fff" />}
      {error && <Text style={styles.errorText}>{error}</Text>}
      {tokens && (
        <FlatList
          data={Object.entries(tokens)}
          keyExtractor={(item) => item[0]}
          renderItem={({ item }) => (
            <View style={styles.tokenRow}><Text style={styles.tokenText}>{item[0]}</Text></View>
          )}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: 250, // Fixed width for the sidebar
    backgroundColor: '#1e1e1e',
    borderRadius: 8,
    marginLeft: 5,
    padding: 10,
  },
  title: { color: '#fff', fontSize: 18, fontWeight: 'bold', marginBottom: 10, textAlign: 'center' },
  errorText: { color: 'red', textAlign: 'center' },
  tokenRow: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  tokenText: {
    color: '#fff',
    fontSize: 16,
  },
});

export default HotTokens;
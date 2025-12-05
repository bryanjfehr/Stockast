/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useEffect, useState, useMemo } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView } from 'react-native';
import { api } from '../services/api';

// OHLCV data format: [timestamp, open, high, low, close, volume]
type OHLCVData = number[][];

const MarketChart: React.FC = () => {
  const [chartData, setChartData] = useState<OHLCVData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchChartData = async () => {
      try {
        setLoading(true);
        const symbol = 'BTC/USDT'; // Hardcoded for now
        const response = await api.get(`/ohlcv/${encodeURIComponent(symbol)}?timeframe=1h&limit=20`);
        setChartData(response.data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch chart data.');
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, []);

  const renderTable = () => {
    if (loading) return <ActivityIndicator size="large" color="#fff" />;
    if (error) return <Text style={styles.errorText}>{`Chart Error: ${error}`}</Text>;
    if (!chartData || chartData.length === 0) return <Text style={styles.text}>No data available.</Text>;

    return (
      <ScrollView>
        <View style={styles.tableHeader}>
          <Text style={styles.headerCell}>Time</Text>
          <Text style={styles.headerCell}>Open</Text>
          <Text style={styles.headerCell}>High</Text>
          <Text style={styles.headerCell}>Low</Text>
          <Text style={styles.headerCell}>Close</Text>
        </View>
        {chartData.map((row, index) => (
          <View key={index} style={styles.tableRow}>
            <Text style={styles.cell}>{new Date(row[0]).toLocaleTimeString()}</Text>
            <Text style={styles.cell}>{row[1].toFixed(2)}</Text>
            <Text style={styles.cell}>{row[2].toFixed(2)}</Text>
            <Text style={styles.cell}>{row[3].toFixed(2)}</Text>
            <Text style={styles.cell}>{row[4].toFixed(2)}</Text>
          </View>
        ))}
      </ScrollView>
    );
  };

  return (
    <View style={styles.container}>
      {renderTable()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1, // Takes up remaining space in the row
    backgroundColor: '#1e1e1e',
    borderRadius: 8,
    marginRight: 5,
    padding: 10,
  },
  text: { color: '#fff', fontSize: 16, textAlign: 'center' },
  errorText: { color: 'red', fontSize: 16, textAlign: 'center' },
  tableHeader: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#555', paddingBottom: 5, marginBottom: 5 },
  headerCell: { flex: 1, color: '#aaa', fontWeight: 'bold', textAlign: 'center' },
  tableRow: { flexDirection: 'row', paddingVertical: 4 },
  cell: { flex: 1, color: '#fff', textAlign: 'center' },
});

export default MarketChart;
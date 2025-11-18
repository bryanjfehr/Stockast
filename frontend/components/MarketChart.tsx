/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useEffect, useState, useMemo } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, useWindowDimensions } from 'react-native';
import { CandlestickChart } from 'react-native-wagmi-charts';
import { api } from '../services/api';

// OHLCV data format: [timestamp, open, high, low, close, volume]
type OHLCVData = number[][];

const MarketChart: React.FC = () => {
  const [chartData, setChartData] = useState<OHLCVData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { width } = useWindowDimensions();

  useEffect(() => {
    const fetchChartData = async () => {
      try {
        console.log('[MarketChart] Fetching chart data...');
        setLoading(true);
        // Fetch 1-hour data for BTC/USDT from MEXC
        const symbol = 'BTC/USDT';
        const response = await api.get(`/ohlcv/${encodeURIComponent(symbol)}?timeframe=1h&limit=100`);
        console.log('[MarketChart] Raw data received:', response.data);
        setChartData(response.data);
        setError(null);
      } catch (err: any) {
        const errorMessage = err.message || 'Failed to fetch chart data.';
        setError(errorMessage);
        console.error('[MarketChart] Fetch error:', err);
      } finally {
        setLoading(false);
        console.log('[MarketChart] Fetch complete.');
      }
    };

    fetchChartData();
  }, []);

  // Memoize the formatted data to prevent re-computation on every render
  const formattedData = useMemo(() => {
    if (!chartData) return [];
    // react-native-wagmi-charts expects this specific object structure
    console.log('[MarketChart] Formatting data for chart...');
    return chartData.map(([timestamp, open, high, low, close]) => ({
      timestamp,
      open,
      high,
      low,
      close,
    }));
  }, [chartData]);

  return (
    <View style={styles.container}>
      {loading && <ActivityIndicator size="large" color="#fff" />}
      {error && <Text style={styles.errorText}>{`Chart Error: ${error}`}</Text>}
      {formattedData.length > 0 && (
        <CandlestickChart.Provider data={formattedData}>
          <CandlestickChart height={300} width={width - 300}>
            <CandlestickChart.Candles positiveColor="#26a69a" negativeColor="#ef5350" />
            <CandlestickChart.Crosshair>
              <CandlestickChart.Tooltip />
            </CandlestickChart.Crosshair>
          </CandlestickChart>
        </CandlestickChart.Provider>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1, // Takes up remaining space in the row
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1e1e1e',
    borderRadius: 8,
    marginRight: 5,
  },
  text: { color: '#fff', fontSize: 16 },
  errorText: { color: 'red', fontSize: 16 },
});

export default MarketChart;
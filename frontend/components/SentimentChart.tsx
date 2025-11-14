import React from 'react';
import { View, Dimensions } from 'react-native';
import { LineChart, CandleChart } from 'react-native-charts-wrapper';
import { useQuery } from '@tanstack/react-query';  // For API fetching
import axios from 'axios';

const { width: screenWidth } = Dimensions.get('window');
const chartWidth = screenWidth - 40;

interface ChartData {
  priceData: Array<{ x: number; y: number; shadowH: number; shadowL: number; open: number; close: number }>;  // For candles
  sentimentData: Array<{ x: number; y: number }>;  // For line
}

const SentimentChart: React.FC<{ symbol: string }> = ({ symbol }) => {
  const { data } = useQuery<ChartData>({
    queryKey: ['sentimentChart', symbol],
    queryFn: async () => {
      const res = await axios.get(`http://your-backend/api/sentiment/${symbol}?include_price=true`);
      // Backend returns { timestamps, prices: [o,h,l,c], sentiments: [...] }
      const timestamps = res.data.timestamps.map((t: string) => new Date(t).getTime());
      return {
        priceData: timestamps.map((ts: number, i: number) => ({
          x: ts,
          y: res.data.prices.closes[i],
          shadowH: res.data.prices.highs[i],
          shadowL: res.data.prices.lows[i],
          open: res.data.prices.opens[i],
          close: res.data.prices.closes[i],
        })),
        sentimentData: timestamps.map((ts: number, i: number) => ({
          x: ts,
          y: res.data.sentiments[i],  // 0-100 EMA
        })),
      };
    },
    refetchInterval: 60000,  // Live update every min
  });

  if (!data) return <View />;

  return (
    <View style={{ height: 400, justifyContent: 'space-between' }}>
      {/* Price Candlestick (Top) */}
      <CandleChart
        style={{ flex: 0.7, width: chartWidth }}
        data={{ dataSets: [{ data: data.priceData, label: 'Price' }] }}
        xAxis={{ valueFormatter: 'date', granularity: 86400000 }}  // Daily
        yAxis={{ left: { axisMinimum: 50000, axisMaximum: 70000 } }}  // BTC range
      />
      
      {/* Sentiment Line (Bottom) */}
      <LineChart
        style={{ flex: 0.3, width: chartWidth }}
        data={{ dataSets: [{ data: data.sentimentData, label: 'Sentiment' }] }}
        xAxis={{ valueFormatter: 'date', granularity: 86400000 }}
        yAxis={{ left: { axisMinimum: 0, axisMaximum: 100 } }}
        description={{ text: 'Sentiment Oscillator (Leading)' }}
        // Add thresholds as reference lines
        extraLines={{ horizontalLines: [
          { value: 70, lineColor: 'red', lineWidth: 1 },
          { value: 30, lineColor: 'orange', lineWidth: 1 },
        ] }}
      />
    </View>
  );
};

export default SentimentChart;
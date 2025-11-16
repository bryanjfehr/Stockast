/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React from 'react';
import { View, StyleSheet } from 'react-native';
import Toolbar from '../components/Toolbar';
import MarketChart from '../components/MarketChart';
import HotTokens from '../components/HotTokens';
import OrderBook from '../components/OrderBook';

const DashboardScreen: React.FC = () => {
  return (
    <View style={styles.container}>
      <Toolbar />
      <View style={styles.mainContent}>
        <MarketChart />
        <HotTokens />
      </View>
      <OrderBook />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  mainContent: {
    flex: 1,
    flexDirection: 'row',
  },
});

export default DashboardScreen;

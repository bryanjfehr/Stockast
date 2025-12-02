/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useEffect, useState, useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';

const MarketChart: React.FC = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Market Chart (Placeholder)</Text>
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
  text: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
});

export default MarketChart;
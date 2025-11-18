/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const OrderBook: React.FC = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Order Book</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 250, // Fixed height for the bottom panel
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1e1e1e',
    borderRadius: 8,
    margin: 10,
  },
  text: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
});

export default OrderBook;
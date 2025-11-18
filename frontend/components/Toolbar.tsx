/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';

const Toolbar: React.FC = () => {
  return (
    <View style={styles.container}>
      <Text style={styles.logo}>Stockast</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 10,
    backgroundColor: '#1e1e1e',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  logo: { color: '#fff', fontSize: 22, fontWeight: 'bold' },
});

export default Toolbar;
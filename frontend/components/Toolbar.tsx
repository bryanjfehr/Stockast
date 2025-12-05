/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import SymbolSelector from './SymbolSelector'; // We will create this component

const Toolbar: React.FC = () => {
  const [modalVisible, setModalVisible] = React.useState(false);

  return (
    <View style={styles.container}>
      <Text style={styles.logo}>Stockast</Text>
      <View style={styles.centerContent}>
        <Pressable onPress={() => setModalVisible(true)}>
          <Text style={styles.dropdownText}>Select Symbol ▼</Text>
        </Pressable>
      </View>
      <View style={styles.rightPlaceholder} />
      <SymbolSelector modalVisible={modalVisible} setModalVisible={setModalVisible} />
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
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dropdownText: {
    color: '#007AFF',
    fontSize: 18,
  },
  rightPlaceholder: {
    // This ensures the center content is truly centered by matching the logo's space
    width: 100, // Adjust this to roughly match the width of the "Stockast" logo
  },
});

export default Toolbar;
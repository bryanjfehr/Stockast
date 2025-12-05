/**
 * Copyright (c) 2024-present, Stockast.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
import React, { useState, useEffect } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  Pressable,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { api } from '../services/api';

interface SymbolSelectorProps {
  modalVisible: boolean;
  setModalVisible: (visible: boolean) => void;
  // onSelectSymbol: (symbol: string) => void; // TODO: Add this to pass selected symbol back
}

const SymbolSelector: React.FC<SymbolSelectorProps> = ({
  modalVisible,
  setModalVisible,
}) => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [filteredSymbols, setFilteredSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (modalVisible) {
      const fetchSymbols = async () => {
        try {
          setLoading(true);
          const response = await api.get<string[]>('/exchange/symbols');
          setSymbols(response.data);
          setFilteredSymbols(response.data);
          setError(null);
        } catch (err) {
          setError('Failed to fetch symbols.');
          console.error(err);
        } finally {
          setLoading(false);
        }
      };
      fetchSymbols();
    }
  }, [modalVisible]);

  const handleSearch = (text: string) => {
    setSearch(text);
    if (text) {
      const filtered = symbols.filter(symbol =>
        symbol.toLowerCase().includes(text.toLowerCase())
      );
      setFilteredSymbols(filtered);
    } else {
      setFilteredSymbols(symbols);
    }
  };

  return (
    <Modal
      animationType="slide"
      transparent={false}
      visible={modalVisible}
      onRequestClose={() => setModalVisible(false)}
    >
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Select a Symbol</Text>
          <Pressable onPress={() => setModalVisible(false)}>
            <Text style={styles.closeButton}>Close</Text>
          </Pressable>
        </View>
        <TextInput
          style={styles.searchInput}
          placeholder="Search symbols..."
          placeholderTextColor="#888"
          value={search}
          onChangeText={handleSearch}
        />
        {loading ? (
          <ActivityIndicator size="large" color="#fff" />
        ) : error ? (
          <Text style={styles.errorText}>{error}</Text>
        ) : (
          <FlatList
            data={filteredSymbols}
            keyExtractor={item => item}
            renderItem={({ item }) => (
              <Pressable onPress={() => { /* TODO: onSelectSymbol(item); */ setModalVisible(false); }}>
                <Text style={styles.symbolItem}>{item}</Text>
              </Pressable>
            )}
          />
        )}
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 15, borderBottomWidth: 1, borderBottomColor: '#333' },
  title: { fontSize: 20, color: '#fff', fontWeight: 'bold' },
  closeButton: { fontSize: 16, color: '#007AFF' },
  searchInput: { height: 40, borderColor: '#555', borderWidth: 1, borderRadius: 5, paddingHorizontal: 10, margin: 15, color: '#fff' },
  symbolItem: { padding: 15, fontSize: 18, color: '#fff', borderBottomWidth: 1, borderBottomColor: '#222' },
  errorText: { color: 'red', textAlign: 'center', marginTop: 20 },
});

export default SymbolSelector;
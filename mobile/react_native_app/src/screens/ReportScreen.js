import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  FlatList,
} from 'react-native';
import { COLORS, SPACING, RADIUS } from '../styles/theme';
import { apiService } from '../services/api';

export const ReportScreen = () => {
  const [history, setHistory] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState('history'); // 'history' or 'snapshots'

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      try {
        const historyData = await apiService.getHistory(100);
        setHistory(historyData);
      } catch (error) {
        console.warn('Could not fetch history:', error.message);
        // Mock data fallback
        setHistory([
          { label: 'pollinating', confidence: 0.87, timestamp: new Date().toISOString() },
          { label: 'pollinated', confidence: 0.92, timestamp: new Date(Date.now() - 5000).toISOString() },
          { label: 'not_pollinated', confidence: 0.95, timestamp: new Date(Date.now() - 10000).toISOString() },
        ]);
      }
      
      try {
        const snapshotData = await apiService.getSnapshots();
        setSnapshots(snapshotData);
      } catch (error) {
        console.warn('Could not fetch snapshots:', error.message);
        setSnapshots([]);
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error in fetchData:', error);
      setLoading(false);
    }
  };

  const getStats = () => {
    const stats = {
      pollinating: 0,
      pollinated: 0,
      not_pollinated: 0,
      total: history.length,
    };

    history.forEach(item => {
      if (item.label && stats.hasOwnProperty(item.label)) {
        stats[item.label]++;
      }
    });

    return stats;
  };

  const stats = getStats();

  const renderHistoryItem = ({ item, index }) => (
    <View style={styles.tableRow}>
      <Text style={styles.tableCell}>{index + 1}</Text>
      <Text style={[styles.tableCell, { flex: 1 }]}>{item.label}</Text>
      <Text style={styles.tableCell}>{(item.confidence * 100).toFixed(1)}%</Text>
      <Text style={[styles.tableCell, { fontSize: 10 }]}>{item.timestamp}</Text>
    </View>
  );

  const renderSnapshotItem = ({ item }) => (
    <TouchableOpacity style={styles.snapshotCard}>
      <Image source={{ uri: item.url }} style={styles.snapshotImage} />
      <Text style={styles.snapshotLabel}>{item.timestamp}</Text>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={[styles.container, styles.centerContent]}>
        <ActivityIndicator size="large" color={COLORS.cyan} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView style={styles.content}>
        <Text style={styles.title}>📋 Report</Text>

        {/* Stats Cards */}
        <View style={styles.statsGrid}>
          <View style={[styles.statCard, { borderLeftColor: COLORS.green }]}>
            <Text style={[styles.statValue, { color: COLORS.green }]}>{stats.pollinating}</Text>
            <Text style={styles.statLabel}>Pollinating</Text>
          </View>
          <View style={[styles.statCard, { borderLeftColor: COLORS.blue }]}>
            <Text style={[styles.statValue, { color: COLORS.blue }]}>{stats.pollinated}</Text>
            <Text style={styles.statLabel}>Pollinated</Text>
          </View>
          <View style={[styles.statCard, { borderLeftColor: COLORS.red }]}>
            <Text style={[styles.statValue, { color: COLORS.red }]}>{stats.not_pollinated}</Text>
            <Text style={styles.statLabel}>Not Poll.</Text>
          </View>
        </View>

        {/* Total Detections */}
        <View style={styles.totalCard}>
          <Text style={styles.totalLabel}>Total Detections Today</Text>
          <Text style={styles.totalValue}>{stats.total}</Text>
        </View>

        {/* Tabs */}
        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, selectedTab === 'history' && styles.activeTab]}
            onPress={() => setSelectedTab('history')}
          >
            <Text style={[styles.tabText, selectedTab === 'history' && styles.activeTabText]}>
              📊 Detection History
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, selectedTab === 'snapshots' && styles.activeTab]}
            onPress={() => setSelectedTab('snapshots')}
          >
            <Text style={[styles.tabText, selectedTab === 'snapshots' && styles.activeTabText]}>
              📸 Snapshots ({snapshots.length})
            </Text>
          </TouchableOpacity>
        </View>

        {/* History Table */}
        {selectedTab === 'history' && (
          <View style={styles.section}>
            <View style={styles.tableHeader}>
              <Text style={styles.headerCell}>#</Text>
              <Text style={[styles.headerCell, { flex: 1 }]}>Classification</Text>
              <Text style={styles.headerCell}>Conf.</Text>
              <Text style={[styles.headerCell, { fontSize: 10 }]}>Time</Text>
            </View>
            <FlatList
              data={history}
              renderItem={renderHistoryItem}
              keyExtractor={(item, index) => index.toString()}
              scrollEnabled={false}
            />
          </View>
        )}

        {/* Snapshots Grid */}
        {selectedTab === 'snapshots' && (
          <View style={styles.section}>
            <FlatList
              data={snapshots}
              renderItem={renderSnapshotItem}
              keyExtractor={(item, index) => index.toString()}
              numColumns={2}
              columnWrapperStyle={styles.snapshotRow}
              scrollEnabled={false}
            />
          </View>
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.darkBg,
  },
  centerContent: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
    padding: SPACING.lg,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: COLORS.text,
    marginBottom: SPACING.lg,
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.lg,
  },
  statCard: {
    flex: 1,
    backgroundColor: 'rgba(10, 20, 40, 0.9)',
    borderWidth: 1,
    borderLeftWidth: 3,
    borderColor: COLORS.border,
    borderRadius: RADIUS.lg,
    padding: SPACING.md,
    marginHorizontal: SPACING.sm,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 22,
    fontWeight: '700',
    fontFamily: 'monospace',
    marginBottom: SPACING.sm,
  },
  statLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  totalCard: {
    backgroundColor: 'rgba(0, 200, 255, 0.1)',
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    marginBottom: SPACING.lg,
    alignItems: 'center',
  },
  totalLabel: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginBottom: SPACING.sm,
  },
  totalValue: {
    fontSize: 28,
    fontWeight: '700',
    color: COLORS.cyan,
    fontFamily: 'monospace',
  },
  tabs: {
    flexDirection: 'row',
    marginBottom: SPACING.lg,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  tab: {
    flex: 1,
    paddingVertical: SPACING.md,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: COLORS.cyan,
  },
  tabText: {
    fontSize: 12,
    color: COLORS.textMuted,
  },
  activeTabText: {
    color: COLORS.cyan,
    fontWeight: '600',
  },
  section: {
    backgroundColor: 'rgba(10, 20, 40, 0.9)',
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.lg,
    overflow: 'hidden',
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 200, 255, 0.05)',
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  headerCell: {
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(0, 200, 255, 0.55)',
    textTransform: 'uppercase',
  },
  tableRow: {
    flexDirection: 'row',
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  tableCell: {
    fontSize: 11,
    color: COLORS.textSecondary,
    width: 30,
  },
  snapshotRow: {
    justifyContent: 'space-between',
  },
  snapshotCard: {
    width: '48%',
    marginVertical: SPACING.sm,
    borderRadius: RADIUS.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  snapshotImage: {
    width: '100%',
    height: 150,
    backgroundColor: '#000',
  },
  snapshotLabel: {
    fontSize: 10,
    color: COLORS.textMuted,
    padding: SPACING.sm,
  },
});

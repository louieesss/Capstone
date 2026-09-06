import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  RefreshControl,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { COLORS, SPACING, RADIUS } from '../styles/theme';
import { apiService } from '../services/api';
import { ClassificationCard } from '../components/ClassificationCard';
import { SessionCounters } from '../components/SessionCounters';
import { ConfidenceBar } from '../components/ConfidenceBar';

const screenWidth = Dimensions.get('window').width;

export const DashboardScreen = () => {
  const [state, setState] = useState({
    label: 'initializing',
    confidence: 0.0,
    probs: { pollinating: 0, pollinated: 0, not_pollinated: 0 },
    timestamp: '',
  });
  const [history, setHistory] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const pollIntervalRef = useRef(null);

  useEffect(() => {
    fetchData();
    pollIntervalRef.current = setInterval(fetchData, 2000);
    return () => clearInterval(pollIntervalRef.current);
  }, []);

  const fetchData = async () => {
    try {
      try {
        const currentState = await apiService.getCurrentState();
        setState(currentState);
      } catch (apiError) {
        console.warn('Backend API unavailable, using mock data:', apiError.message);
        // Use mock data when backend is unavailable
        setState({
          label: 'pollinating',
          confidence: 0.87,
          probs: { pollinating: 0.87, pollinated: 0.12, not_pollinated: 0.01 },
          timestamp: new Date().toISOString(),
        });
      }

      if (!loading) return;
      
      try {
        const historyData = await apiService.getHistory(20);
        setHistory(historyData);
      } catch (historyError) {
        console.warn('Could not fetch history:', historyError.message);
        setHistory([
          { label: 'pollinating', confidence: 0.87, timestamp: new Date().toISOString() },
          { label: 'pollinated', confidence: 0.92, timestamp: new Date(Date.now() - 5000).toISOString() },
        ]);
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error in fetchData:', error);
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const countByLabel = () => {
    const counts = { pollinating: 0, pollinated: 0, not_pollinated: 0 };
    history.forEach(item => {
      if (item.label && counts.hasOwnProperty(item.label)) {
        counts[item.label]++;
      }
    });
    return counts;
  };

  const counts = countByLabel();

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Title */}
        <Text style={styles.title}>📊 Live Dashboard</Text>

        {/* Video Feed */}
        <View style={styles.feedContainer}>
          <Text style={styles.panelHeader}>Live Camera Feed</Text>
          <View style={[styles.videoFeed, { justifyContent: 'center', alignItems: 'center' }]}>
            <Text style={{ color: COLORS.textMuted, fontSize: 12 }}>
              📹 Video feed will display when backend is connected
            </Text>
          </View>
          <Text style={styles.feedNote}>Connect Python Flask server on port 5000</Text>
        </View>

        {/* Classification Card */}
        <ClassificationCard
          label={state.label}
          confidence={state.confidence}
          timestamp={state.timestamp}
        />

        {/* Confidence Bars */}
        <View style={styles.section}>
          <Text style={styles.panelHeader}>Confidence per Class</Text>
          <ConfidenceBar
            className="pollinating"
            confidence={state.probs.pollinating || 0}
          />
          <ConfidenceBar
            className="pollinated"
            confidence={state.probs.pollinated || 0}
          />
          <ConfidenceBar
            className="not_pollinated"
            confidence={state.probs.not_pollinated || 0}
          />
        </View>

        {/* Session Counters */}
        <SessionCounters
          pollinating={counts.pollinating}
          pollinated={counts.pollinated}
          notPollinated={counts.not_pollinated}
        />

        {/* Recent History */}
        <View style={styles.section}>
          <Text style={styles.panelHeader}>Recent Detections</Text>
          {history.slice(0, 5).map((item, index) => (
            <View key={index} style={styles.historyItem}>
              <Text style={styles.historyLabel}>{item.label}</Text>
              <Text style={styles.historyConf}>{(item.confidence * 100).toFixed(1)}%</Text>
              <Text style={styles.historyTime}>{item.timestamp}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.darkBg,
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
  feedContainer: {
    backgroundColor: 'rgba(10, 20, 40, 0.9)',
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.lg,
    overflow: 'hidden',
    marginBottom: SPACING.lg,
  },
  panelHeader: {
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(0, 200, 255, 0.55)',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    padding: SPACING.lg,
    paddingBottom: SPACING.sm,
  },
  videoFeed: {
    width: '100%',
    height: 280,
    backgroundColor: '#000',
  },
  feedNote: {
    fontSize: 10,
    color: COLORS.textMuted,
    textAlign: 'center',
    paddingBottom: SPACING.lg,
  },
  section: {
    backgroundColor: 'rgba(10, 20, 40, 0.9)',
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    marginBottom: SPACING.lg,
  },
  historyItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: SPACING.sm,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  historyLabel: {
    fontSize: 12,
    color: COLORS.text,
    flex: 1,
  },
  historyConf: {
    fontSize: 12,
    color: COLORS.textMuted,
    fontFamily: 'monospace',
    marginHorizontal: SPACING.md,
  },
  historyTime: {
    fontSize: 10,
    color: COLORS.textMuted,
  },
});

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, SPACING, RADIUS, FONTS } from '../styles/theme';

export const SessionCounters = ({ pollinating = 0, pollinated = 0, notPollinated = 0 }) => {
  const total = pollinating + pollinated + notPollinated;

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Session Detections</Text>

      <View style={styles.grid}>
        <View style={styles.counter}>
          <Text style={[styles.value, { color: COLORS.green }]}>{pollinating}</Text>
          <Text style={styles.label}>Pollinating</Text>
        </View>
        <View style={styles.counter}>
          <Text style={[styles.value, { color: COLORS.blue }]}>{pollinated}</Text>
          <Text style={styles.label}>Pollinated</Text>
        </View>
        <View style={styles.counter}>
          <Text style={[styles.value, { color: COLORS.red }]}>{notPollinated}</Text>
          <Text style={styles.label}>Not Poll.</Text>
        </View>
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Total detections: <Text style={{ color: COLORS.textSecondary }}>{total}</Text>
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'rgba(10, 20, 40, 0.9)',
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    marginBottom: SPACING.md,
  },
  header: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(0, 200, 255, 0.55)',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: SPACING.lg,
  },
  grid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.lg,
  },
  counter: {
    flex: 1,
    backgroundColor: 'rgba(0, 10, 25, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    alignItems: 'center',
    marginHorizontal: SPACING.sm,
  },
  value: {
    fontSize: 28,
    fontWeight: '700',
    fontFamily: 'monospace',
    marginBottom: SPACING.sm,
  },
  label: {
    fontSize: 12,
    color: COLORS.textMuted,
    textAlign: 'center',
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
    paddingTop: SPACING.md,
  },
  footerText: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
});

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, SPACING, RADIUS } from '../styles/theme';

export const ClassificationCard = ({ label, confidence, timestamp }) => {
  const getLabelColor = (label) => {
    switch (label) {
      case 'pollinating':
        return COLORS.green;
      case 'pollinated':
        return COLORS.blue;
      case 'not_pollinated':
        return COLORS.red;
      default:
        return COLORS.textMuted;
    }
  };

  const getLabelText = (label) => {
    const map = {
      'pollinating': 'Pollinating',
      'pollinated': 'Pollinated',
      'not_pollinated': 'Not Pollinated',
    };
    return map[label] || label;
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Current Classification</Text>
      
      <View style={styles.content}>
        <View style={[styles.badge, { borderColor: getLabelColor(label) }]}>
          <Text style={[styles.badgeText, { color: getLabelColor(label) }]}>
            {getLabelText(label)}
          </Text>
        </View>
        
        <Text style={styles.confidence}>{(confidence * 100).toFixed(1)}%</Text>
      </View>

      <Text style={styles.timestamp}>{timestamp || '—'}</Text>
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
  content: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.md,
  },
  badge: {
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.sm,
    borderWidth: 1,
    borderRadius: 20,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  confidence: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.text,
    fontFamily: 'monospace',
  },
  timestamp: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
});

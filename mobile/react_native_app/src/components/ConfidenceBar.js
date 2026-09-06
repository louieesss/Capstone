import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS, SPACING, RADIUS } from '../styles/theme';

export const ConfidenceBar = ({ label, confidence, className }) => {
  const getGradientColor = (className) => {
    switch (className) {
      case 'pollinating':
        return COLORS.green;
      case 'pollinated':
        return COLORS.blue;
      case 'not_pollinated':
        return COLORS.red;
      default:
        return COLORS.cyan;
    }
  };

  const getLabelText = (className) => {
    const map = {
      'pollinating': 'Pollinating',
      'pollinated': 'Pollinated',
      'not_pollinated': 'Not Pollinated',
    };
    return map[className] || className;
  };

  const percentage = Math.min(Math.max(confidence * 100, 0), 100);

  return (
    <View style={styles.container}>
      <View style={styles.labelRow}>
        <Text style={styles.label}>{getLabelText(className)}</Text>
        <Text style={styles.percentage}>{percentage.toFixed(1)}%</Text>
      </View>
      <View style={styles.barContainer}>
        <View
          style={[
            styles.bar,
            {
              width: `${percentage}%`,
              backgroundColor: getGradientColor(className),
            },
          ]}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: SPACING.md,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.sm,
  },
  label: {
    fontSize: 12,
    color: COLORS.textMuted,
  },
  percentage: {
    fontSize: 12,
    color: COLORS.textMuted,
    fontFamily: 'monospace',
  },
  barContainer: {
    height: 8,
    backgroundColor: '#0F1C2E',
    borderRadius: RADIUS.sm,
    overflow: 'hidden',
  },
  bar: {
    height: '100%',
    borderRadius: RADIUS.sm,
  },
});

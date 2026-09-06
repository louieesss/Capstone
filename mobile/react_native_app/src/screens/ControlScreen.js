import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { COLORS, SPACING, RADIUS } from '../styles/theme';
import { apiService } from '../services/api';

export const ControlScreen = () => {
  const [config, setConfig] = useState({
    camera_enabled: true,
    confidence_threshold: 0.35,
    infer_every: 3,
    stable_frames: 5,
    jpeg_quality: 80,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const data = await apiService.getConfig();
      setConfig(data);
      setLoading(false);
    } catch (error) {
      console.warn('Could not fetch config from backend:', error.message);
      // Use default config if backend unavailable
      setLoading(false);
    }
  };

  const handleConfigChange = async (field, value) => {
    const newConfig = { ...config, [field]: value };
    setConfig(newConfig);
    
    try {
      setSaving(true);
      await apiService.updateConfig({ [field]: value });
      setSaving(false);
    } catch (error) {
      console.warn('Could not save config to backend:', error.message);
      // Still keep the local state updated even if backend save fails
      setSaving(false);
    }
  };

  const handleSnapshot = async () => {
    try {
      setSaving(true);
      await apiService.takeSnapshot();
      Alert.alert('Success', 'Snapshot captured');
      setSaving(false);
    } catch (error) {
      console.warn('Backend API unavailable:', error.message);
      Alert.alert('Info', 'Backend not connected. Local mode only.');
      setSaving(false);
    }
  };

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
        <Text style={styles.title}>⚙️ Control Panel</Text>

        {/* Camera Control */}
        <View style={styles.section}>
          <Text style={styles.sectionHeader}>Camera Settings</Text>
          
          <View style={styles.controlItem}>
            <Text style={styles.label}>Camera Enabled</Text>
            <Switch
              value={config.camera_enabled}
              onValueChange={(value) => handleConfigChange('camera_enabled', value)}
              trackColor={{ false: '#3f3f3f', true: COLORS.green }}
              thumbColor={config.camera_enabled ? COLORS.cyan : '#f4f3f4'}
            />
          </View>

          <View style={styles.controlItem}>
            <View>
              <Text style={styles.label}>JPEG Quality</Text>
              <Text style={styles.value}>{config.jpeg_quality}%</Text>
            </View>
            <View style={styles.sliderPlaceholder}>
              <Text style={styles.hint}>Adjust in Web UI</Text>
            </View>
          </View>
        </View>

        {/* Model Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionHeader}>Model Settings</Text>
          
          <View style={styles.controlItem}>
            <View>
              <Text style={styles.label}>Confidence Threshold</Text>
              <Text style={styles.value}>{(config.confidence_threshold * 100).toFixed(1)}%</Text>
            </View>
            <View style={styles.sliderPlaceholder}>
              <Text style={styles.hint}>Adjust in Web UI</Text>
            </View>
          </View>

          <View style={styles.controlItem}>
            <View>
              <Text style={styles.label}>Inference Interval</Text>
              <Text style={styles.value}>{config.infer_every} frames</Text>
            </View>
            <View style={styles.sliderPlaceholder}>
              <Text style={styles.hint}>Adjust in Web UI</Text>
            </View>
          </View>

          <View style={styles.controlItem}>
            <View>
              <Text style={styles.label}>Stable Frames Count</Text>
              <Text style={styles.value}>{config.stable_frames}</Text>
            </View>
            <View style={styles.sliderPlaceholder}>
              <Text style={styles.hint}>Adjust in Web UI</Text>
            </View>
          </View>
        </View>

        {/* Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionHeader}>Actions</Text>
          
          <TouchableOpacity
            style={[styles.button, styles.primaryButton]}
            onPress={handleSnapshot}
            disabled={saving}
          >
            <Text style={styles.buttonText}>📸 Take Snapshot</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.button, styles.secondaryButton]}>
            <Text style={styles.buttonText}>🔄 Restart Camera</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.button, styles.secondaryButton]}>
            <Text style={styles.buttonText}>🗑️ Clear History</Text>
          </TouchableOpacity>
        </View>

        {/* Info */}
        <View style={styles.section}>
          <Text style={styles.sectionHeader}>System Info</Text>
          <Text style={styles.info}>Model: EfficientNet-B3</Text>
          <Text style={styles.info}>Accuracy: 82.6%</Text>
          <Text style={styles.info}>Classes: Pollinating, Pollinated, Not Pollinated</Text>
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
  section: {
    backgroundColor: 'rgba(10, 20, 40, 0.9)',
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.lg,
    padding: SPACING.lg,
    marginBottom: SPACING.lg,
  },
  sectionHeader: {
    fontSize: 12,
    fontWeight: '600',
    color: 'rgba(0, 200, 255, 0.55)',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: SPACING.lg,
  },
  controlItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SPACING.md,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  label: {
    fontSize: 13,
    color: COLORS.text,
    fontWeight: '500',
  },
  value: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginTop: SPACING.xs,
    fontFamily: 'monospace',
  },
  sliderPlaceholder: {
    alignItems: 'flex-end',
  },
  hint: {
    fontSize: 10,
    color: COLORS.textMuted,
  },
  button: {
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.lg,
    borderRadius: RADIUS.md,
    alignItems: 'center',
    marginVertical: SPACING.sm,
  },
  primaryButton: {
    backgroundColor: COLORS.cyan,
  },
  secondaryButton: {
    backgroundColor: 'rgba(0, 200, 255, 0.1)',
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  buttonText: {
    fontSize: 13,
    fontWeight: '600',
    color: COLORS.cyan,
  },
  info: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginVertical: SPACING.sm,
  },
});

import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  StatusBar,
} from 'react-native';
import { SafeAreaView, SafeAreaProvider } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius, shadows } from './src/lib/theme';
import CameraScreen from './src/screens/CameraScreen';
import MonitorScreen from './src/screens/MonitorScreen';

type Tab = 'camera' | 'monitor';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('monitor');

  return (
    <SafeAreaProvider>
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={colors.background} />

        <LinearGradient
          colors={[colors.background, '#0f0f12', colors.background]}
          style={StyleSheet.absoluteFill}
        />

        <SafeAreaView style={styles.safeArea}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.logoRow}>
              <LinearGradient
                colors={colors.gradientPrimary as [string, string]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.logoIcon}
              >
                <Text style={styles.logoEmoji}>👁️</Text>
              </LinearGradient>
              <View style={styles.logoText}>
                <Text style={styles.logoTitle}>Argos</Text>
                <Text style={styles.logoSubtitle}>Vigilancia Inteligente</Text>
              </View>
            </View>

            <View style={styles.statusPill}>
              <View style={[styles.statusDot, { backgroundColor: colors.primary }]} />
              <Text style={styles.statusPillText}>Online</Text>
            </View>
          </View>

          {/* Content */}
          <View style={styles.content}>
            {activeTab === 'camera' ? <CameraScreen /> : <MonitorScreen />}
          </View>

          {/* Tab Bar */}
          <View style={styles.tabBarContainer}>
            <View style={styles.tabBar}>
              <TabButton
                icon="📹"
                label="Cámara"
                isActive={activeTab === 'camera'}
                onPress={() => setActiveTab('camera')}
              />
              <TabButton
                icon="👁️"
                label="Monitor"
                isActive={activeTab === 'monitor'}
                onPress={() => setActiveTab('monitor')}
              />
            </View>
          </View>
        </SafeAreaView>
      </View>
    </SafeAreaProvider>
  );
}

function TabButton({
  icon,
  label,
  isActive,
  onPress
}: {
  icon: string;
  label: string;
  isActive: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.tab, isActive && styles.tabActive]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      {isActive && (
        <LinearGradient
          colors={colors.gradientPrimary as [string, string]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.tabActiveBackground}
        />
      )}
      <Text style={styles.tabIcon}>{icon}</Text>
      <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  safeArea: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  logoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  logoIcon: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoEmoji: {
    fontSize: 24,
  },
  logoText: {
    gap: 2,
  },
  logoTitle: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.textPrimary,
    letterSpacing: -0.5,
  },
  logoSubtitle: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.full,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusPillText: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  content: {
    flex: 1,
  },
  tabBarContainer: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.xl,
    padding: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.lg,
    overflow: 'hidden',
  },
  tabActive: {
    position: 'relative',
  },
  tabActiveBackground: {
    ...StyleSheet.absoluteFillObject,
    opacity: 0.15,
  },
  tabIcon: {
    fontSize: 20,
  },
  tabLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    fontWeight: '500',
  },
  tabLabelActive: {
    color: colors.primary,
    fontWeight: '600',
  },
});

import React, { useState, useEffect } from 'react';
import {
    StyleSheet,
    View,
    Text,
    TouchableOpacity,
    Image,
    ScrollView,
    RefreshControl,
    Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius, shadows } from '../lib/theme';
import { useDetectionStream } from '../hooks/useDetectionStream';
import { checkHealth, getAlertHistory, Alert } from '../lib/api';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function MonitorScreen() {
    const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
    const [refreshing, setRefreshing] = useState(false);
    const [alertHistory, setAlertHistory] = useState<Alert[]>([]);

    const {
        status,
        trackingData,
        frame,
        zones,
        alerts,
        error,
        connect,
        disconnect
    } = useDetectionStream({ includeFrames: true });

    useEffect(() => {
        checkBackend();
    }, []);

    const checkBackend = async () => {
        const online = await checkHealth();
        setBackendOnline(online);
        if (online) {
            const history = await getAlertHistory();
            setAlertHistory(history);
        }
    };

    const onRefresh = async () => {
        setRefreshing(true);
        await checkBackend();
        setRefreshing(false);
    };

    const isConnected = status === 'connected';
    const allAlerts = [...alerts, ...alertHistory].slice(0, 10);

    return (
        <ScrollView
            style={styles.container}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            refreshControl={
                <RefreshControl
                    refreshing={refreshing}
                    onRefresh={onRefresh}
                    tintColor={colors.primary}
                />
            }
        >
            {/* Connection Card */}
            <View style={styles.card}>
                <View style={styles.cardHeader}>
                    <Text style={styles.cardIcon}>📡</Text>
                    <Text style={styles.cardTitle}>Conexión</Text>
                </View>

                <View style={styles.statusGrid}>
                    <StatusItem
                        label="Backend"
                        status={backendOnline === null ? 'loading' : backendOnline ? 'online' : 'offline'}
                    />
                    <StatusItem
                        label="Stream"
                        status={status === 'connecting' ? 'loading' : isConnected ? 'online' : 'offline'}
                    />
                </View>

                <TouchableOpacity
                    style={[styles.mainButton, isConnected && styles.mainButtonStop]}
                    onPress={isConnected ? disconnect : connect}
                    disabled={!backendOnline}
                    activeOpacity={0.8}
                >
                    <LinearGradient
                        colors={isConnected ? colors.gradientDanger as [string, string] : colors.gradientPrimary as [string, string]}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 0 }}
                        style={styles.mainButtonGradient}
                    >
                        <Text style={styles.mainButtonIcon}>{isConnected ? '⏹' : '▶️'}</Text>
                        <Text style={styles.mainButtonText}>
                            {isConnected ? 'Detener Stream' : 'Conectar'}
                        </Text>
                    </LinearGradient>
                </TouchableOpacity>
            </View>

            {/* Error Banner */}
            {error && (
                <View style={styles.errorBanner}>
                    <Text style={styles.errorIcon}>⚠️</Text>
                    <Text style={styles.errorText}>{error}</Text>
                </View>
            )}

            {/* Video Feed */}
            <View style={styles.card}>
                <View style={styles.cardHeader}>
                    <Text style={styles.cardIcon}>📺</Text>
                    <Text style={styles.cardTitle}>Video en Vivo</Text>
                    {isConnected && (
                        <View style={styles.liveBadge}>
                            <View style={styles.liveDot} />
                            <Text style={styles.liveText}>EN VIVO</Text>
                        </View>
                    )}
                </View>

                <View style={styles.videoContainer}>
                    {frame ? (
                        <Image
                            source={{ uri: frame }}
                            style={styles.videoImage}
                            resizeMode="contain"
                        />
                    ) : (
                        <View style={styles.videoPlaceholder}>
                            <Text style={styles.placeholderIcon}>📹</Text>
                            <Text style={styles.placeholderText}>
                                {isConnected ? 'Cargando stream...' : 'Conecta para ver video'}
                            </Text>
                        </View>
                    )}
                </View>
            </View>

            {/* Stats */}
            {trackingData && (
                <View style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardIcon}>📊</Text>
                        <Text style={styles.cardTitle}>Estadísticas</Text>
                    </View>

                    <View style={styles.statsRow}>
                        <StatBox
                            value={trackingData.total_objects}
                            label="Objetos"
                            color={colors.primary}
                        />
                        <StatBox
                            value={`${trackingData.inference_time_ms.toFixed(0)}ms`}
                            label="Latencia"
                            color={colors.accent}
                        />
                        <StatBox
                            value={zones.length}
                            label="Zonas"
                            color={colors.warning}
                        />
                    </View>

                    {Object.keys(trackingData.counts).length > 0 && (
                        <View style={styles.countsList}>
                            {Object.entries(trackingData.counts).map(([name, count]) => (
                                <View key={name} style={styles.countItem}>
                                    <Text style={styles.countName}>{name}</Text>
                                    <View style={styles.countBadge}>
                                        <Text style={styles.countValue}>{count}</Text>
                                    </View>
                                </View>
                            ))}
                        </View>
                    )}
                </View>
            )}

            {/* Alerts */}
            <View style={styles.card}>
                <View style={styles.cardHeader}>
                    <Text style={styles.cardIcon}>🚨</Text>
                    <Text style={styles.cardTitle}>Alertas</Text>
                    {allAlerts.length > 0 && (
                        <View style={styles.alertCountBadge}>
                            <Text style={styles.alertCountText}>{allAlerts.length}</Text>
                        </View>
                    )}
                </View>

                {allAlerts.length === 0 ? (
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyIcon}>✨</Text>
                        <Text style={styles.emptyText}>Sin alertas recientes</Text>
                    </View>
                ) : (
                    <View style={styles.alertsList}>
                        {allAlerts.slice(0, 5).map((alert, index) => (
                            <AlertItem key={`${alert.id}-${index}`} alert={alert} />
                        ))}
                    </View>
                )}
            </View>

            <View style={{ height: spacing.xl }} />
        </ScrollView>
    );
}

function StatusItem({ label, status }: { label: string; status: 'online' | 'offline' | 'loading' }) {
    const dotColor = status === 'online' ? colors.success : status === 'loading' ? colors.warning : colors.danger;
    const statusText = status === 'online' ? 'Conectado' : status === 'loading' ? 'Cargando...' : 'Desconectado';

    return (
        <View style={styles.statusItem}>
            <Text style={styles.statusLabel}>{label}</Text>
            <View style={styles.statusValue}>
                <View style={[styles.statusDot, { backgroundColor: dotColor }]} />
                <Text style={styles.statusValueText}>{statusText}</Text>
            </View>
        </View>
    );
}

function StatBox({ value, label, color }: { value: string | number; label: string; color: string }) {
    return (
        <View style={styles.statBox}>
            <Text style={[styles.statValue, { color }]}>{value}</Text>
            <Text style={styles.statLabel}>{label}</Text>
        </View>
    );
}

function AlertItem({ alert }: { alert: Alert }) {
    const isDanger = alert.zone_type === 'danger';

    return (
        <View style={[styles.alertItem, isDanger && styles.alertItemDanger]}>
            <View style={[styles.alertIconContainer, isDanger ? styles.alertIconDanger : styles.alertIconWarning]}>
                <Text style={styles.alertItemIcon}>{isDanger ? '🚨' : '⚠️'}</Text>
            </View>
            <View style={styles.alertContent}>
                <Text style={styles.alertMessage} numberOfLines={1}>{alert.message}</Text>
                <Text style={styles.alertTime}>
                    {new Date(alert.timestamp * 1000).toLocaleTimeString()}
                </Text>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    scrollContent: {
        padding: spacing.lg,
        gap: spacing.md,
    },
    card: {
        backgroundColor: colors.surface,
        borderRadius: borderRadius.lg,
        padding: spacing.lg,
        borderWidth: 1,
        borderColor: colors.border,
        ...shadows.sm,
    },
    cardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.sm,
        marginBottom: spacing.md,
    },
    cardIcon: {
        fontSize: 18,
    },
    cardTitle: {
        flex: 1,
        fontSize: fontSize.lg,
        fontWeight: '600',
        color: colors.textPrimary,
    },
    statusGrid: {
        flexDirection: 'row',
        gap: spacing.md,
        marginBottom: spacing.lg,
    },
    statusItem: {
        flex: 1,
        backgroundColor: colors.surfaceElevated,
        borderRadius: borderRadius.md,
        padding: spacing.md,
        gap: spacing.xs,
    },
    statusLabel: {
        fontSize: fontSize.xs,
        color: colors.textMuted,
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    statusValue: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.xs,
    },
    statusDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },
    statusValueText: {
        fontSize: fontSize.sm,
        color: colors.textPrimary,
        fontWeight: '500',
    },
    mainButton: {
        borderRadius: borderRadius.md,
        overflow: 'hidden',
    },
    mainButtonStop: {},
    mainButtonGradient: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: spacing.sm,
        paddingVertical: spacing.md,
    },
    mainButtonIcon: {
        fontSize: 18,
    },
    mainButtonText: {
        fontSize: fontSize.base,
        fontWeight: '600',
        color: '#fff',
    },
    errorBanner: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.sm,
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderRadius: borderRadius.md,
        padding: spacing.md,
        borderWidth: 1,
        borderColor: 'rgba(239, 68, 68, 0.3)',
    },
    errorIcon: {
        fontSize: 16,
    },
    errorText: {
        flex: 1,
        fontSize: fontSize.sm,
        color: colors.danger,
    },
    liveBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.xs,
        backgroundColor: 'rgba(239, 68, 68, 0.15)',
        paddingHorizontal: spacing.sm,
        paddingVertical: spacing.xs,
        borderRadius: borderRadius.full,
    },
    liveDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        backgroundColor: colors.danger,
    },
    liveText: {
        fontSize: fontSize.xs,
        fontWeight: '600',
        color: colors.danger,
    },
    videoContainer: {
        aspectRatio: 16 / 9,
        backgroundColor: colors.background,
        borderRadius: borderRadius.md,
        overflow: 'hidden',
    },
    videoImage: {
        width: '100%',
        height: '100%',
    },
    videoPlaceholder: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        gap: spacing.sm,
    },
    placeholderIcon: {
        fontSize: 48,
        opacity: 0.3,
    },
    placeholderText: {
        fontSize: fontSize.sm,
        color: colors.textMuted,
    },
    statsRow: {
        flexDirection: 'row',
        gap: spacing.sm,
    },
    statBox: {
        flex: 1,
        backgroundColor: colors.surfaceElevated,
        borderRadius: borderRadius.md,
        padding: spacing.md,
        alignItems: 'center',
        gap: spacing.xs,
    },
    statValue: {
        fontSize: fontSize.xxl,
        fontWeight: '700',
    },
    statLabel: {
        fontSize: fontSize.xs,
        color: colors.textMuted,
        textTransform: 'uppercase',
    },
    countsList: {
        marginTop: spacing.md,
        gap: spacing.xs,
    },
    countItem: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: colors.surfaceElevated,
        borderRadius: borderRadius.sm,
        paddingVertical: spacing.sm,
        paddingHorizontal: spacing.md,
    },
    countName: {
        fontSize: fontSize.sm,
        color: colors.textPrimary,
        textTransform: 'capitalize',
    },
    countBadge: {
        backgroundColor: colors.primary + '20',
        paddingHorizontal: spacing.sm,
        paddingVertical: spacing.xs,
        borderRadius: borderRadius.sm,
    },
    countValue: {
        fontSize: fontSize.sm,
        fontWeight: '600',
        color: colors.primary,
    },
    alertCountBadge: {
        backgroundColor: colors.danger,
        width: 20,
        height: 20,
        borderRadius: 10,
        alignItems: 'center',
        justifyContent: 'center',
    },
    alertCountText: {
        fontSize: fontSize.xs,
        fontWeight: '600',
        color: '#fff',
    },
    emptyState: {
        alignItems: 'center',
        paddingVertical: spacing.xl,
        gap: spacing.sm,
    },
    emptyIcon: {
        fontSize: 32,
    },
    emptyText: {
        fontSize: fontSize.sm,
        color: colors.textMuted,
    },
    alertsList: {
        gap: spacing.sm,
    },
    alertItem: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.md,
        backgroundColor: colors.surfaceElevated,
        borderRadius: borderRadius.md,
        padding: spacing.md,
    },
    alertItemDanger: {
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
    },
    alertIconContainer: {
        width: 36,
        height: 36,
        borderRadius: 18,
        alignItems: 'center',
        justifyContent: 'center',
    },
    alertIconDanger: {
        backgroundColor: 'rgba(239, 68, 68, 0.2)',
    },
    alertIconWarning: {
        backgroundColor: 'rgba(245, 158, 11, 0.2)',
    },
    alertItemIcon: {
        fontSize: 16,
    },
    alertContent: {
        flex: 1,
        gap: 2,
    },
    alertMessage: {
        fontSize: fontSize.sm,
        color: colors.textPrimary,
        fontWeight: '500',
    },
    alertTime: {
        fontSize: fontSize.xs,
        color: colors.textMuted,
    },
});

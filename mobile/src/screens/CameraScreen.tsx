import React, { useState, useRef, useEffect } from 'react';
import {
    StyleSheet,
    View,
    Text,
    TouchableOpacity,
    ActivityIndicator,
    Dimensions
} from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius, shadows } from '../lib/theme';
import { API_CONFIG } from '../lib/api';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export default function CameraScreen() {
    const [permission, requestPermission] = useCameraPermissions();
    const [facing, setFacing] = useState<CameraType>('back');
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamStatus, setStreamStatus] = useState<'idle' | 'streaming' | 'error'>('idle');
    const cameraRef = useRef<CameraView>(null);
    const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const isStreamingRef = useRef(false);

    useEffect(() => {
        return () => {
            stopStreaming();
        };
    }, []);

    const startStreaming = async () => {
        if (!cameraRef.current) return;

        setIsStreaming(true);
        isStreamingRef.current = true;
        setStreamStatus('streaming');

        const sendFrame = async () => {
            if (!cameraRef.current || !isStreamingRef.current) return;

            try {
                const photo = await cameraRef.current.takePictureAsync({
                    quality: 0.4,
                    base64: true,
                    skipProcessing: true,
                    shutterSound: false,
                });

                if (photo?.base64 && isStreamingRef.current) {
                    const response = await fetch(`${API_CONFIG.baseUrl}/api/frame`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ frame: photo.base64 }),
                    });

                    if (!response.ok) {
                        console.log('Frame send failed:', response.status);
                    }
                }
            } catch (err) {
                console.log('Frame error:', err);
                setStreamStatus('error');
            }
        };

        // Enviar frames cada 150ms (~7 FPS para no saturar)
        streamIntervalRef.current = setInterval(sendFrame, 150);
    };

    const stopStreaming = () => {
        isStreamingRef.current = false;
        setIsStreaming(false);
        setStreamStatus('idle');
        if (streamIntervalRef.current) {
            clearInterval(streamIntervalRef.current);
            streamIntervalRef.current = null;
        }
    };

    const toggleCameraFacing = () => {
        setFacing(current => (current === 'back' ? 'front' : 'back'));
    };

    if (!permission) {
        return (
            <View style={styles.container}>
                <ActivityIndicator size="large" color={colors.primary} />
            </View>
        );
    }

    if (!permission.granted) {
        return (
            <View style={styles.container}>
                <View style={styles.permissionCard}>
                    <View style={styles.permissionIconContainer}>
                        <LinearGradient
                            colors={colors.gradientPrimary as [string, string]}
                            style={styles.permissionIcon}
                        >
                            <Text style={styles.permissionEmoji}>📹</Text>
                        </LinearGradient>
                    </View>
                    <Text style={styles.permissionTitle}>Permiso de Cámara</Text>
                    <Text style={styles.permissionText}>
                        VisionMind necesita acceso a tu cámara para transmitir video al servidor de detección.
                    </Text>
                    <TouchableOpacity
                        style={styles.permissionButton}
                        onPress={requestPermission}
                        activeOpacity={0.8}
                    >
                        <LinearGradient
                            colors={colors.gradientPrimary as [string, string]}
                            start={{ x: 0, y: 0 }}
                            end={{ x: 1, y: 0 }}
                            style={styles.permissionButtonGradient}
                        >
                            <Text style={styles.permissionButtonText}>Permitir Cámara</Text>
                        </LinearGradient>
                    </TouchableOpacity>
                </View>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <CameraView ref={cameraRef} style={styles.camera} facing={facing} />

            {/* Overlay con posicionamiento absoluto */}
            <View style={styles.overlay}>
                {/* Top Bar */}
                <View style={styles.topBar}>
                    <View style={[styles.statusPill, isStreaming && styles.statusPillActive]}>
                        <View style={[styles.statusDot, isStreaming && styles.statusDotActive]} />
                        <Text style={styles.statusText}>
                            {isStreaming ? 'Transmitiendo' : 'En espera'}
                        </Text>
                    </View>
                </View>

                {/* Center - Server Info */}
                <View style={styles.serverCard}>
                    <Text style={styles.serverLabel}>Servidor</Text>
                    <Text style={styles.serverUrl}>{API_CONFIG.baseUrl}</Text>
                </View>

                {/* Bottom Controls */}
                <View style={styles.controls}>
                    {/* Flip Camera */}
                    <TouchableOpacity
                        style={styles.controlButton}
                        onPress={toggleCameraFacing}
                        activeOpacity={0.7}
                    >
                        <Text style={styles.controlIcon}>🔄</Text>
                    </TouchableOpacity>

                    {/* Main Button */}
                    <TouchableOpacity
                        style={styles.mainButtonContainer}
                        onPress={isStreaming ? stopStreaming : startStreaming}
                        activeOpacity={0.9}
                    >
                        <LinearGradient
                            colors={isStreaming ? colors.gradientDanger as [string, string] : colors.gradientPrimary as [string, string]}
                            style={styles.mainButton}
                        >
                            <View style={styles.mainButtonInner}>
                                <Text style={styles.mainButtonIcon}>{isStreaming ? '⏹' : '▶️'}</Text>
                            </View>
                        </LinearGradient>
                        <Text style={styles.mainButtonLabel}>
                            {isStreaming ? 'Detener' : 'Iniciar'}
                        </Text>
                    </TouchableOpacity>

                    {/* Settings placeholder */}
                    <TouchableOpacity style={styles.controlButton} activeOpacity={0.7}>
                        <Text style={styles.controlIcon}>⚙️</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    camera: {
        flex: 1,
    },
    overlay: {
        ...StyleSheet.absoluteFillObject,
        justifyContent: 'space-between',
        padding: spacing.lg,
    },
    topBar: {
        alignItems: 'flex-start',
    },
    statusPill: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: spacing.sm,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.sm,
        borderRadius: borderRadius.full,
        backgroundColor: 'rgba(0,0,0,0.6)',
    },
    statusPillActive: {
        backgroundColor: 'rgba(16, 185, 129, 0.3)',
    },
    statusDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: colors.textMuted,
    },
    statusDotActive: {
        backgroundColor: colors.primary,
    },
    statusText: {
        color: '#fff',
        fontSize: fontSize.sm,
        fontWeight: '500',
    },
    serverCard: {
        alignSelf: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(0,0,0,0.6)',
        paddingHorizontal: spacing.lg,
        paddingVertical: spacing.md,
        borderRadius: borderRadius.md,
        gap: spacing.xs,
    },
    serverLabel: {
        fontSize: fontSize.xs,
        color: colors.textMuted,
        textTransform: 'uppercase',
        letterSpacing: 1,
    },
    serverUrl: {
        fontSize: fontSize.sm,
        color: colors.textPrimary,
        fontFamily: 'monospace',
    },
    controls: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
    },
    controlButton: {
        width: 56,
        height: 56,
        borderRadius: 28,
        backgroundColor: 'rgba(0,0,0,0.5)',
        justifyContent: 'center',
        alignItems: 'center',
        ...shadows.sm,
    },
    controlIcon: {
        fontSize: 24,
    },
    mainButtonContainer: {
        alignItems: 'center',
        gap: spacing.sm,
    },
    mainButton: {
        width: 80,
        height: 80,
        borderRadius: 40,
        justifyContent: 'center',
        alignItems: 'center',
        ...shadows.lg,
    },
    mainButtonInner: {
        width: 68,
        height: 68,
        borderRadius: 34,
        backgroundColor: 'rgba(255,255,255,0.1)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    mainButtonIcon: {
        fontSize: 28,
    },
    mainButtonLabel: {
        fontSize: fontSize.sm,
        color: '#fff',
        fontWeight: '600',
    },
    permissionCard: {
        margin: spacing.lg,
        padding: spacing.xl,
        backgroundColor: colors.surface,
        borderRadius: borderRadius.xl,
        alignItems: 'center',
        gap: spacing.lg,
        ...shadows.md,
    },
    permissionIconContainer: {
        marginBottom: spacing.sm,
    },
    permissionIcon: {
        width: 80,
        height: 80,
        borderRadius: 40,
        justifyContent: 'center',
        alignItems: 'center',
    },
    permissionEmoji: {
        fontSize: 36,
    },
    permissionTitle: {
        fontSize: fontSize.xl,
        fontWeight: '700',
        color: colors.textPrimary,
        textAlign: 'center',
    },
    permissionText: {
        fontSize: fontSize.base,
        color: colors.textSecondary,
        textAlign: 'center',
        lineHeight: 22,
    },
    permissionButton: {
        width: '100%',
        borderRadius: borderRadius.md,
        overflow: 'hidden',
    },
    permissionButtonGradient: {
        paddingVertical: spacing.md,
        alignItems: 'center',
    },
    permissionButtonText: {
        fontSize: fontSize.base,
        fontWeight: '600',
        color: '#fff',
    },
});

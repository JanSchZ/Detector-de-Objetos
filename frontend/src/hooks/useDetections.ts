'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { API_ENDPOINTS, TrackingData, DetectionMessage, Zone, ZoneEvent, Alert } from '@/lib/api';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface UseDetectionsOptions {
    includeFrames?: boolean;
    autoConnect?: boolean;
}

interface UseDetectionsReturn {
    status: ConnectionStatus;
    trackingData: TrackingData | null;
    frame: string | null;
    frameSize: { width: number; height: number } | null;
    streamStatus: string | null;
    zones: Zone[];
    zoneEvents: ZoneEvent[];
    alerts: Alert[];
    error: string | null;
    fps: number;
    connect: () => void;
    disconnect: () => void;
    sendCommand: (command: object) => void;
}

/**
 * Hook for real-time object detection with tracking, zones and alerts via WebSocket
 */
export function useDetections(options: UseDetectionsOptions = {}): UseDetectionsReturn {
    const { includeFrames = true, autoConnect = true } = options;


    const [status, setStatus] = useState<ConnectionStatus>('disconnected');
    const [trackingData, setTrackingData] = useState<TrackingData | null>(null);
    const [frame, setFrame] = useState<string | null>(null);
    const [frameSize, setFrameSize] = useState<{ width: number; height: number } | null>(null);
    const [streamStatus, setStreamStatus] = useState<string | null>(null);
    const [zones, setZones] = useState<Zone[]>([]);
    const [zoneEvents, setZoneEvents] = useState<ZoneEvent[]>([]);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [fps, setFps] = useState(0);

    const wsRef = useRef<WebSocket | null>(null);
    const frameCountRef = useRef(0);
    const lastFpsUpdateRef = useRef(Date.now());
    const reconnectAttemptsRef = useRef(0);
    const shouldReconnectRef = useRef(false);
    const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
    const maxReconnectAttempts = 8;

    const hasValidFrameSize = (size?: { width: number; height: number } | null) =>
        !!size && size.width > 0 && size.height > 0;

    const sendCommand = useCallback((command: object) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(command));
        }
    }, []);

    const clearReconnectTimer = () => {
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
        }
    };

    const connect = useCallback(() => {
        if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
            return;
        }

        shouldReconnectRef.current = true;
        clearReconnectTimer();

        setStatus('connecting');
        setError(null);
        setStreamStatus(null);

        const ws = new WebSocket(API_ENDPOINTS.websocket);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[WS] Connected, sending start command');
            reconnectAttemptsRef.current = 0;
            ws.send(JSON.stringify({
                command: 'start',
                include_frames: includeFrames,
            }));
        };

        ws.onmessage = (event) => {
            try {
                const message: DetectionMessage = JSON.parse(event.data);
                console.log('[WS] Message received:', message.type);

                switch (message.type) {
                    case 'started':
                        console.log('[WS] Detection started, setting connected');
                        setStatus('connected');
                        if (hasValidFrameSize(message.frame_size)) {
                            setFrameSize(message.frame_size!);
                        } else {
                            setFrameSize(null);
                        }
                        setStreamStatus('Esperando frames...');
                        if (message.zones) setZones(message.zones);
                        break;

                    case 'detection':
                        if (message.data) {
                            setTrackingData(message.data);

                            // Refresh frame size with real dimensions once detections start
                            if (hasValidFrameSize(message.data.frame_size)) {
                                setFrameSize(message.data.frame_size);
                            }
                            setStreamStatus(null);

                            // Update FPS counter
                            frameCountRef.current++;
                            const now = Date.now();
                            if (now - lastFpsUpdateRef.current >= 1000) {
                                setFps(Math.round(frameCountRef.current * 1000 / (now - lastFpsUpdateRef.current)));
                                frameCountRef.current = 0;
                                lastFpsUpdateRef.current = now;
                            }
                        }
                        if (message.frame) {
                            setFrame(`data:image/jpeg;base64,${message.frame}`);
                        }
                        if (message.zone_events) {
                            setZoneEvents(message.zone_events);
                        }
                        if (message.alerts && message.alerts.length > 0) {
                            setAlerts(prev => [...prev, ...message.alerts!].slice(-20));
                        }
                        if (message.zones) {
                            setZones(message.zones);
                        }
                        break;

                    case 'status':
                        if (message.message) {
                            setStreamStatus(message.message);
                        }
                        break;

                    case 'zone_added':
                        if (message.zone) {
                            setZones(prev => [...prev.filter(z => z.id !== message.zone!.id), message.zone!]);
                        }
                        break;

                    case 'zone_removed':
                        if (message.zone_id) {
                            setZones(prev => prev.filter(z => z.id !== message.zone_id));
                        }
                        break;

                    case 'zones_cleared':
                        setZones([]);
                        break;

                    case 'error':
                        setError(message.message || 'Unknown error');
                        setStatus('error');
                        setStreamStatus(null);
                        break;
                }
            } catch (err) {
                console.error('Failed to parse WebSocket message:', err);
            }
        };

        ws.onerror = () => {
            setError('WebSocket connection error');
            setStatus('error');
            setStreamStatus(null);
        };

        ws.onclose = () => {
            wsRef.current = null;
            if (shouldReconnectRef.current) {
                const attempt = reconnectAttemptsRef.current + 1;
                reconnectAttemptsRef.current = attempt;
                if (attempt > maxReconnectAttempts) {
                    shouldReconnectRef.current = false;
                    setStatus('error');
                    setError('No se pudo reconectar con el backend');
                    return;
                }
                const delay = Math.min(5000, 500 * attempt);
                setStatus('connecting');
                reconnectTimerRef.current = setTimeout(connect, delay);
            } else {
                setStatus('disconnected');
            }
        };
    }, [includeFrames]);

    const disconnect = useCallback(() => {
        console.log('[WS] Disconnect called');
        shouldReconnectRef.current = false;
        clearReconnectTimer();
        if (wsRef.current) {
            if (wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ command: 'stop' }));
            }
            wsRef.current.close();
            wsRef.current = null;
        }
        setStatus('disconnected');
        setTrackingData(null);
        setFrame(null);
        setFps(0);
        setAlerts([]);
        setStreamStatus(null);
    }, []);

    // Cleanup on unmount only - use empty deps to avoid re-running
    useEffect(() => {
        return () => {
            console.log('[WS] Component unmounting, cleaning up');
            shouldReconnectRef.current = false;
            clearReconnectTimer();
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, []);

    // Auto-connect on mount if enabled
    useEffect(() => {
        if (autoConnect) {
            // Small delay to ensure component is fully mounted
            const timer = setTimeout(() => {
                connect();
            }, 100);
            return () => clearTimeout(timer);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Only run once on mount

    return {
        status,
        trackingData,
        frame,
        frameSize,
        zones,
        zoneEvents,
        alerts,
        error,
        fps,
        streamStatus,
        connect,
        disconnect,
        sendCommand,
    };
}

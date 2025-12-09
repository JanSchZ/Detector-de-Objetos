import { useState, useEffect, useRef, useCallback } from 'react';
import { API_CONFIG, DetectionMessage, TrackingData, Zone, Alert } from '../lib/api';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface UseDetectionStreamOptions {
    includeFrames?: boolean;
    autoConnect?: boolean;
}

interface UseDetectionStreamReturn {
    status: ConnectionStatus;
    trackingData: TrackingData | null;
    frame: string | null;
    zones: Zone[];
    alerts: Alert[];
    error: string | null;
    connect: () => void;
    disconnect: () => void;
}

/**
 * Hook for viewing detection stream from backend
 */
export function useDetectionStream(options: UseDetectionStreamOptions = {}): UseDetectionStreamReturn {
    const { includeFrames = true, autoConnect = false } = options;

    const [status, setStatus] = useState<ConnectionStatus>('disconnected');
    const [trackingData, setTrackingData] = useState<TrackingData | null>(null);
    const [frame, setFrame] = useState<string | null>(null);
    const [zones, setZones] = useState<Zone[]>([]);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        setStatus('connecting');
        setError(null);

        const ws = new WebSocket(API_CONFIG.endpoints.websocket);
        wsRef.current = ws;

        ws.onopen = () => {
            ws.send(JSON.stringify({ command: 'start', include_frames: includeFrames }));
        };

        ws.onmessage = (event) => {
            try {
                const message: DetectionMessage = JSON.parse(event.data);

                switch (message.type) {
                    case 'started':
                        setStatus('connected');
                        if (message.zones) setZones(message.zones);
                        break;

                    case 'detection':
                        if (message.data) setTrackingData(message.data);
                        if (message.frame) setFrame(`data:image/jpeg;base64,${message.frame}`);
                        if (message.zones) setZones(message.zones);
                        if (message.alerts?.length) {
                            setAlerts(prev => [...prev, ...message.alerts!].slice(-20));
                        }
                        break;

                    case 'error':
                        setError(message.message || 'Error');
                        setStatus('error');
                        break;
                }
            } catch (err) {
                console.error('Failed to parse message:', err);
            }
        };

        ws.onerror = () => {
            setError('Connection error');
            setStatus('error');
        };

        ws.onclose = () => {
            setStatus('disconnected');
            wsRef.current = null;
        };
    }, [includeFrames]);

    const disconnect = useCallback(() => {
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
    }, []);

    useEffect(() => {
        if (autoConnect) connect();
        return () => { disconnect(); };
    }, [autoConnect, connect, disconnect]);

    return { status, trackingData, frame, zones, alerts, error, connect, disconnect };
}

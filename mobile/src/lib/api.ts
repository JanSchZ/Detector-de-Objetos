/**
 * VisionMind Mobile - API Configuration
 */

// Default to localhost, update with actual server URL
export const API_CONFIG = {
    // Tu Mac Mini IP - el móvil se conecta aquí
    baseUrl: process.env.EXPO_PUBLIC_API_URL || 'http://192.168.3.39:8000',

    get wsUrl() {
        return this.baseUrl.replace('http', 'ws');
    },

    get endpoints() {
        return {
            health: `${this.baseUrl}/api/health`,
            config: `${this.baseUrl}/api/config`,
            zones: `${this.baseUrl}/api/zones`,
            alertsHistory: `${this.baseUrl}/api/alerts/history`,
            websocket: `${this.wsUrl}/ws/detect`,
        };
    }
};

// Types
export interface TrackedObject {
    tracker_id: number;
    class_id: number;
    class_name: string;
    class_name_es: string;
    confidence: number;
    bbox: [number, number, number, number];
}

export interface Zone {
    id: string;
    name: string;
    type: 'warning' | 'danger';
    color: string;
}

export interface Alert {
    id: string;
    title: string;
    message: string;
    zone_type: 'warning' | 'danger';
    timestamp: number;
}

export interface TrackingData {
    objects: TrackedObject[];
    counts: Record<string, number>;
    total_objects: number;
    inference_time_ms: number;
    timestamp: number;
}

export interface DetectionMessage {
    type: 'detection' | 'started' | 'error';
    data?: TrackingData;
    frame?: string;
    zones?: Zone[];
    alerts?: Alert[];
    message?: string;
}

// API Functions
export async function checkHealth(): Promise<boolean> {
    try {
        const response = await fetch(API_CONFIG.endpoints.health);
        return response.ok;
    } catch {
        return false;
    }
}

export async function getAlertHistory(): Promise<Alert[]> {
    try {
        const response = await fetch(API_CONFIG.endpoints.alertsHistory);
        if (!response.ok) return [];
        const data = await response.json();
        return data.alerts || [];
    } catch {
        return [];
    }
}

/**
 * API configuration and client for VisionMind backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE_URL =
    process.env.NEXT_PUBLIC_WS_URL ||
    API_BASE_URL.replace(/^http/, 'ws');

export const API_ENDPOINTS = {
    health: `${API_BASE_URL}/api/health`,
    cameras: `${API_BASE_URL}/api/cameras`,
    cameraStatus: `${API_BASE_URL}/api/camera/status`,
    config: `${API_BASE_URL}/api/config`,
    classes: `${API_BASE_URL}/api/classes`,
    models: `${API_BASE_URL}/api/models`,
    zones: `${API_BASE_URL}/api/zones`,
    alertsConfig: `${API_BASE_URL}/api/alerts/config`,
    alertsHistory: `${API_BASE_URL}/api/alerts/history`,
    alertsTest: `${API_BASE_URL}/api/alerts/test`,
    assistantChat: `${API_BASE_URL}/api/assistant/chat`,
    websocket: `${WS_BASE_URL}/ws/detect`,
};


// ===== Configuration Types =====

export interface DetectionConfig {
    video_source: 'webcam' | 'ip_camera';
    webcam_index: number;
    ip_camera_url: string;
    model_type: 'detection' | 'pose';
    model_size: string;
    confidence_threshold: number;
    iou_threshold: number;
    pose_enabled: boolean;
    pose_model_size: string;
    enabled_classes: number[];
    counting_enabled: boolean;
    counting_region: { x: number; y: number; width: number; height: number } | null;
    show_confidence: boolean;
    show_labels: boolean;
    box_color: string;
    font_size: number;
    max_fps: number;
    frame_skip: number;
}

// ===== Detection Types =====

export interface Keypoint {
    x: number;
    y: number;
    confidence: number;
    name: string;
}

export interface TrackedObject {
    tracker_id: number;
    class_id: number;
    class_name: string;
    class_name_es: string;
    confidence: number;
    bbox: [number, number, number, number];
    center: [number, number];
    bottom_center: [number, number];
    keypoints?: Keypoint[];
}

export interface TrackingData {
    objects: TrackedObject[];
    counts: Record<string, number>;
    total_objects: number;
    active_tracker_ids: number[];
    inference_time_ms: number;
    frame_size: { width: number; height: number };
    timestamp: number;
}

// ===== Zone Types =====

export interface Zone {
    id: string;
    name: string;
    type: 'warning' | 'danger';
    polygon: [number, number][];
    color: string;
    enabled: boolean;
}

export interface ZoneEvent {
    tracker_id: number;
    class_name: string;
    zone_id: string;
    zone_name: string;
    zone_type: 'warning' | 'danger';
    event_type: 'enter' | 'inside' | 'exit';
    timestamp: number;
}

// ===== Alert Types =====

export interface Alert {
    id: string;
    title: string;
    message: string;
    priority: string;
    zone_type: 'warning' | 'danger';
    tracker_id: number;
    class_name: string;
    timestamp: number;
    sent: boolean;
}

export interface AlertConfig {
    enabled: boolean;
    ntfy_server: string;
    ntfy_topic: string;
    min_confidence: number;
    min_frames_in_zone: number;
    cooldown_seconds: number;
    alert_classes: string[];
}

export interface CameraStatus {
    status: 'ok';
    source: 'ip_camera' | 'webcam';
    url?: string;
    index?: number;
    resolution: { width: number; height: number };
}

// ===== WebSocket Message Types =====

export interface DetectionMessage {
    type: 'detection' | 'started' | 'error' | 'zone_added' | 'zone_removed' | 'zones_cleared' | 'status';
    data?: TrackingData;
    frame?: string;
    config?: DetectionConfig;
    frame_size?: { width: number; height: number };
    zones?: Zone[];
    zone_events?: ZoneEvent[];
    alerts?: Alert[];
    message?: string;
    level?: 'info' | 'warning';
    zone?: Zone;
    zone_id?: string;
}

// ===== API Functions =====

export async function getConfig(): Promise<DetectionConfig> {
    const response = await fetch(API_ENDPOINTS.config);
    if (!response.ok) throw new Error('Failed to fetch config');
    return response.json();
}

export async function updateConfig(updates: Partial<DetectionConfig>): Promise<DetectionConfig> {
    const response = await fetch(API_ENDPOINTS.config, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update config');
    const result = await response.json();
    return result.config;
}

export async function getZones(): Promise<Zone[]> {
    const response = await fetch(API_ENDPOINTS.zones);
    if (!response.ok) throw new Error('Failed to fetch zones');
    const result = await response.json();
    return result.zones;
}

export async function createZone(zone: Omit<Zone, 'enabled'> & { enabled?: boolean }): Promise<Zone> {
    const response = await fetch(API_ENDPOINTS.zones, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(zone),
    });
    if (!response.ok) throw new Error('Failed to create zone');
    const result = await response.json();
    return result.zone;
}

export async function deleteZone(zoneId: string): Promise<void> {
    const response = await fetch(`${API_ENDPOINTS.zones}/${zoneId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete zone');
}

export async function updateZone(zone: Zone): Promise<Zone> {
    const response = await fetch(`${API_ENDPOINTS.zones}/${zone.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            id: zone.id,
            name: zone.name,
            type: zone.type,
            polygon: zone.polygon,
            color: zone.color,
            enabled: zone.enabled,
        }),
    });
    if (!response.ok) throw new Error('Failed to update zone');
    const result = await response.json();
    return result.zone;
}

export async function toggleZone(zoneId: string): Promise<Zone> {
    const response = await fetch(`${API_ENDPOINTS.zones}/${zoneId}/toggle`, { method: 'PATCH' });
    if (!response.ok) throw new Error('Failed to toggle zone');
    const result = await response.json();
    return result.zone;
}

export async function resetZones(): Promise<Zone[]> {
    const response = await fetch(`${API_ENDPOINTS.zones}/reset`, { method: 'POST' });
    if (!response.ok) throw new Error('Failed to reset zones');
    const result = await response.json();
    return result.zones;
}

export async function checkCamera(): Promise<CameraStatus> {
    const response = await fetch(API_ENDPOINTS.cameraStatus);
    if (!response.ok) {
        const text = await response.text();
        try {
            const parsed = JSON.parse(text);
            throw new Error(parsed.detail || text || 'No se pudo verificar la cámara');
        } catch {
            throw new Error(text || 'No se pudo verificar la cámara');
        }
    }
    return response.json();
}

export async function getAlertConfig(): Promise<AlertConfig> {
    const response = await fetch(API_ENDPOINTS.alertsConfig);
    if (!response.ok) throw new Error('Failed to fetch alert config');
    return response.json();
}

export async function updateAlertConfig(updates: Partial<AlertConfig>): Promise<AlertConfig> {
    const response = await fetch(API_ENDPOINTS.alertsConfig, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error('Failed to update alert config');
    const result = await response.json();
    return result.config;
}

export async function getAlertHistory(): Promise<Alert[]> {
    const response = await fetch(API_ENDPOINTS.alertsHistory);
    if (!response.ok) throw new Error('Failed to fetch alert history');
    const result = await response.json();
    return result.alerts;
}

export async function testAlert(): Promise<Alert> {
    const response = await fetch(API_ENDPOINTS.alertsTest, { method: 'POST' });
    if (!response.ok) throw new Error('Failed to send test alert');
    const result = await response.json();
    return result.alert;
}

export async function checkHealth(): Promise<boolean> {
    try {
        const response = await fetch(API_ENDPOINTS.health);
        return response.ok;
    } catch {
        return false;
    }
}

export async function getAvailableClasses(): Promise<{ classes: { id: number; name: string }[]; total: number }> {
    const response = await fetch(API_ENDPOINTS.classes);
    if (!response.ok) throw new Error('Failed to fetch classes');
    return response.json();
}

export async function getAvailableModels(): Promise<{
    models: { id: string; name: string; file: string; description: string }[];
    detection_models?: { id: string; name: string; description: string }[];
    pose_models?: { id: string; name: string; description: string }[];
}> {
    const response = await fetch(API_ENDPOINTS.models);
    if (!response.ok) throw new Error('Failed to fetch models');
    return response.json();
}

// ===== Camera Types =====

export interface CameraInfo {
    index: number;
    name: string;
    resolution: { width: number; height: number };
    available: boolean;
}

export interface CamerasResponse {
    cameras: CameraInfo[];
    total: number;
    has_ip_camera_configured: boolean;
    ip_camera_url: string | null;
    current_source: 'webcam' | 'ip_camera';
    current_webcam_index: number;
}

export async function getAvailableCameras(): Promise<CamerasResponse> {
    const response = await fetch(API_ENDPOINTS.cameras);
    if (!response.ok) throw new Error('Failed to fetch cameras');
    return response.json();
}

// ===== AI Assistant =====

export interface AssistantResponse {
    response: string;
    config_changed: boolean;
    new_config: DetectionConfig | null;
    zones_changed?: boolean;
}

export async function sendAssistantMessage(
    message: string,
    history?: { role: string; content: string }[],
    image?: string | null
): Promise<AssistantResponse> {
    const response = await fetch(API_ENDPOINTS.assistantChat, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history, image }),
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Assistant error');
    }
    return response.json();
}

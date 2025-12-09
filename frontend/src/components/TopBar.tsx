'use client';

import { CamerasResponse } from '@/lib/api';

interface TopBarProps {
    onMenuClick: () => void;
    onSettingsClick: () => void;
    onFullscreenToggle: () => void;
    onScreenshot: () => void;
    isConnected: boolean;
    isFullscreen: boolean;
    backendStatus: 'checking' | 'online' | 'offline';
    fps: number;
    inferenceTime: number;
    // Camera selector
    camerasInfo: CamerasResponse | null;
    onCameraChange: (index: number) => void;
    onSourceChange: (source: 'webcam' | 'ip_camera') => void;
}

/**
 * Minimal top bar with controls and camera selector
 */
export function TopBar({
    onMenuClick,
    onSettingsClick,
    onFullscreenToggle,
    onScreenshot,
    isConnected,
    isFullscreen,
    backendStatus,
    fps,
    inferenceTime,
    camerasInfo,
    onCameraChange,
    onSourceChange,
}: TopBarProps) {
    const hasMultipleCameras = camerasInfo && (camerasInfo.total > 1 || camerasInfo.has_ip_camera_configured);

    return (
        <header className="h-12 bg-card/80 backdrop-blur-sm border-b border-border flex items-center justify-between px-3 z-30">
            {/* Left: Menu + Brand */}
            <div className="flex items-center gap-2">
                <button
                    onClick={onMenuClick}
                    className="p-2 rounded hover:bg-secondary transition-colors"
                    aria-label="Menu"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                    </svg>
                </button>

                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-primary/15 flex items-center justify-center">
                        <svg className="w-3.5 h-3.5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                    </div>
                    <span className="text-sm font-medium hidden sm:inline">VisionMind</span>
                </div>

                {/* Camera Selector */}
                {hasMultipleCameras && camerasInfo && (
                    <div className="ml-4 flex items-center gap-2">
                        <svg className="w-4 h-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        <select
                            className="text-xs bg-secondary border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-primary"
                            value={camerasInfo.current_source === 'ip_camera' ? 'ip' : camerasInfo.current_webcam_index}
                            onChange={(e) => {
                                const val = e.target.value;
                                if (val === 'ip') {
                                    onSourceChange('ip_camera');
                                } else {
                                    onSourceChange('webcam');
                                    onCameraChange(parseInt(val, 10));
                                }
                            }}
                        >
                            {camerasInfo.cameras.map((cam) => (
                                <option key={cam.index} value={cam.index}>
                                    {cam.name} ({cam.resolution.width}x{cam.resolution.height})
                                </option>
                            ))}
                            {camerasInfo.has_ip_camera_configured && (
                                <option value="ip">📱 Cámara IP</option>
                            )}
                        </select>
                    </div>
                )}
            </div>

            {/* Center: Stats (when connected) */}
            {isConnected && (
                <div className="hidden md:flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1.5">
                        <span className="text-muted-foreground">FPS</span>
                        <span className="font-mono font-medium text-primary">{fps}</span>
                    </div>
                    <div className="w-px h-4 bg-border" />
                    <div className="flex items-center gap-1.5">
                        <span className="text-muted-foreground">Inferencia</span>
                        <span className="font-mono">{inferenceTime.toFixed(1)}ms</span>
                    </div>
                </div>
            )}

            {/* Right: Actions */}
            <div className="flex items-center gap-1">
                {/* Connection Status */}
                <div className={`status-badge mr-2 ${isConnected ? 'connected' : backendStatus === 'online' ? 'connecting' : 'disconnected'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${backendStatus === 'checking' ? 'bg-muted-foreground animate-pulse' :
                            isConnected ? 'bg-primary animate-pulse' :
                                backendStatus === 'online' ? 'bg-yellow-500 animate-pulse' : 'bg-muted-foreground'
                        }`} />
                    <span className="hidden sm:inline">
                        {backendStatus === 'checking' ? 'Verificando' :
                            isConnected ? 'En vivo' :
                                backendStatus === 'online' ? 'Conectando...' : 'Offline'}
                    </span>
                </div>

                {/* Screenshot */}
                <button
                    onClick={onScreenshot}
                    className="p-2 rounded hover:bg-secondary transition-colors"
                    aria-label="Captura de pantalla"
                    title="Captura de pantalla"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </button>

                {/* Settings */}
                <button
                    onClick={onSettingsClick}
                    className="p-2 rounded hover:bg-secondary transition-colors"
                    aria-label="Configuración"
                    title="Configuración"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                </button>

                {/* Fullscreen */}
                <button
                    onClick={onFullscreenToggle}
                    className="p-2 rounded hover:bg-secondary transition-colors"
                    aria-label={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
                    title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
                >
                    {isFullscreen ? (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                        </svg>
                    ) : (
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
                        </svg>
                    )}
                </button>
            </div>
        </header>
    );
}


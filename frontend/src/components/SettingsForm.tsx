'use client';

import { useState, useEffect } from 'react';
import { DetectionConfig, updateConfig, checkCamera, CameraStatus } from '@/lib/api';

interface SettingsFormProps {
    config: DetectionConfig | null;
    onConfigChange: (config: DetectionConfig) => void;
}

/**
 * Settings panel for configuring detection parameters
 */
export function SettingsForm({ config, onConfigChange }: SettingsFormProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [localIpUrl, setLocalIpUrl] = useState('');
    const [cameraStatus, setCameraStatus] = useState<string | null>(null);
    const [isCheckingCamera, setIsCheckingCamera] = useState(false);

    // Sincronizar URL local con config
    useEffect(() => {
        if (config?.ip_camera_url) {
            setLocalIpUrl(config.ip_camera_url);
        }
    }, [config?.ip_camera_url]);

    if (!config) return null;

    const handleChange = async (updates: Partial<DetectionConfig>) => {
        setIsSaving(true);
        try {
            const newConfig = await updateConfig(updates);
            onConfigChange(newConfig);
        } catch (error) {
            console.error('Failed to update config:', error);
        } finally {
            setIsSaving(false);
        }
    };

    // Guardar URL solo cuando pierde el foco
    const handleIpUrlBlur = () => {
        if (localIpUrl !== config.ip_camera_url) {
            handleChange({ ip_camera_url: localIpUrl });
            setCameraStatus(null);
        }
    };

    const handleTestCamera = async () => {
        setIsCheckingCamera(true);
        setCameraStatus(null);
        try {
            const status: CameraStatus = await checkCamera();
            const res = status?.resolution;
            if (res?.width && res?.height) {
                setCameraStatus(`OK: ${status.source === 'ip_camera' ? 'IP Cam' : 'Webcam'} ${res.width}x${res.height}`);
            } else {
                setCameraStatus('Stream verificado');
            }
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'No se pudo probar la cámara';
            setCameraStatus(msg);
        } finally {
            setIsCheckingCamera(false);
        }
    };

    return (
        <div className="card">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between"
            >
                <h3 className="text-lg font-semibold">Configuración</h3>
                <svg
                    className={`w-5 h-5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {isOpen && (
                <div className="mt-4 space-y-4">
                    {/* Video Source */}
                    <div>
                        <label className="block text-sm font-medium mb-2">Fuente de Video</label>
                        <select
                            value={config.video_source}
                            onChange={(e) => handleChange({ video_source: e.target.value as 'webcam' | 'ip_camera' })}
                            className="input select"
                            disabled={isSaving}
                        >
                            <option value="webcam">Webcam</option>
                            <option value="ip_camera">Cámara IP (Celular)</option>
                        </select>
                    </div>

                    {/* IP Camera URL - con estado local */}
                    {config.video_source === 'ip_camera' && (
                        <div>
                            <label className="block text-sm font-medium mb-2">URL Cámara IP</label>
                            <div className="flex flex-col gap-2">
                                <input
                                    type="text"
                                    value={localIpUrl}
                                    onChange={(e) => setLocalIpUrl(e.target.value)}
                                    onBlur={handleIpUrlBlur}
                                    onKeyDown={(e) => e.key === 'Enter' && handleIpUrlBlur()}
                                    placeholder="http://192.168.1.100:8080/videofeed"
                                    className="input"
                                    disabled={isSaving}
                                />
                                <div className="flex gap-2 items-center">
                                    <button
                                        type="button"
                                        onClick={handleTestCamera}
                                        className="btn btn-secondary text-xs px-3"
                                        disabled={isSaving || isCheckingCamera}
                                    >
                                        {isCheckingCamera ? 'Probando...' : 'Probar stream'}
                                    </button>
                                    {cameraStatus && (
                                        <span className="text-xs text-muted-foreground">{cameraStatus}</span>
                                    )}
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    Presiona Enter o haz clic fuera para guardar
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Webcam Index */}
                    {config.video_source === 'webcam' && (
                        <div>
                            <label className="block text-sm font-medium mb-2">Índice de Webcam</label>
                            <input
                                type="number"
                                min="0"
                                max="10"
                                value={config.webcam_index}
                                onChange={(e) => handleChange({ webcam_index: parseInt(e.target.value) || 0 })}
                                className="input"
                                disabled={isSaving}
                            />
                        </div>
                    )}

                    {/* Confidence Threshold */}
                    <div>
                        <label className="block text-sm font-medium mb-2">
                            Umbral de Confianza: {(config.confidence_threshold * 100).toFixed(0)}%
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            value={config.confidence_threshold * 100}
                            onChange={(e) => handleChange({ confidence_threshold: parseInt(e.target.value) / 100 })}
                            className="slider w-full"
                            disabled={isSaving}
                        />
                    </div>

                    {/* Max FPS */}
                    <div>
                        <label className="block text-sm font-medium mb-2">
                            FPS Máximo: {config.max_fps}
                        </label>
                        <input
                            type="range"
                            min="5"
                            max="60"
                            value={config.max_fps}
                            onChange={(e) => handleChange({ max_fps: parseInt(e.target.value) })}
                            className="slider w-full"
                            disabled={isSaving}
                        />
                    </div>

                    {/* Visual Options */}
                    <div className="flex flex-wrap gap-4">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={config.show_labels}
                                onChange={(e) => handleChange({ show_labels: e.target.checked })}
                                className="w-4 h-4 rounded border-border bg-secondary text-primary focus:ring-primary"
                                disabled={isSaving}
                            />
                            <span className="text-sm">Mostrar etiquetas</span>
                        </label>

                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={config.show_confidence}
                                onChange={(e) => handleChange({ show_confidence: e.target.checked })}
                                className="w-4 h-4 rounded border-border bg-secondary text-primary focus:ring-primary"
                                disabled={isSaving}
                            />
                            <span className="text-sm">Mostrar % confianza</span>
                        </label>
                    </div>

                    {/* Box Color */}
                    <div>
                        <label className="block text-sm font-medium mb-2">Color de Cajas</label>
                        <div className="flex items-center gap-3">
                            <input
                                type="color"
                                value={config.box_color}
                                onChange={(e) => handleChange({ box_color: e.target.value })}
                                className="w-10 h-10 rounded cursor-pointer border border-border"
                                disabled={isSaving}
                            />
                            <span className="text-sm font-mono text-muted-foreground">{config.box_color}</span>
                        </div>
                    </div>

                    {isSaving && (
                        <p className="text-xs text-muted-foreground animate-pulse">Guardando...</p>
                    )}
                </div>
            )}
        </div>
    );
}

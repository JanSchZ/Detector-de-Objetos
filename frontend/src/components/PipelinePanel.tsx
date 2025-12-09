'use client';

import React, { useState, useEffect, useCallback } from 'react';
import PresetSelector from './PresetSelector';

interface Backend {
    backend_id: string;
    backend_type: string;
    enabled: boolean;
    model_name: string;
    capabilities: {
        supports_pose: boolean;
        supports_tracking: boolean;
        max_fps: number;
        supported_targets: string[];
    };
}

interface FusionConfig {
    strategy: string;
    min_backends_agree: number;
    iou_threshold: number;
    prefer_pose_from: string | null;
    confidence_aggregation: string;
}

interface PipelineStatus {
    active_preset: string | null;
    backends: Backend[];
    fusion: FusionConfig;
    capabilities: {
        supports_pose: boolean;
        supports_tracking: boolean;
        max_fps: number;
        backends_count: number;
    };
}

const FUSION_STRATEGIES = [
    { id: 'parallel', name: 'Parallel Merge', icon: '🔀', description: 'Combina todas las detecciones' },
    { id: 'consensus', name: 'Consensus', icon: '🤝', description: 'Solo si 2+ backends coinciden' },
    { id: 'cascade', name: 'Cascade', icon: '⛓️', description: 'YOLO detecta, DLC refina' },
    { id: 'weighted', name: 'Weighted', icon: '⚖️', description: 'Pondera por confiabilidad' },
    { id: 'first_wins', name: 'First Wins', icon: '🥇', description: 'Usa el primer backend' },
];

const BACKEND_TYPES = [
    { id: 'yolo', name: 'YOLO 11', icon: '⚡', color: 'blue' },
    { id: 'deeplabcut', name: 'DeepLabCut', icon: '🔬', color: 'purple' },
    { id: 'sleap', name: 'SLEAP', icon: '🐁', color: 'green' },
];

const PipelinePanel: React.FC<{ className?: string }> = ({ className = '' }) => {
    const [status, setStatus] = useState<PipelineStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [showAddBackend, setShowAddBackend] = useState(false);
    const [newBackendType, setNewBackendType] = useState('yolo');
    const [newModelName, setNewModelName] = useState('');

    const fetchStatus = useCallback(async () => {
        try {
            const response = await fetch('/api/pipeline/status');
            if (response.ok) {
                const data = await response.json();
                setStatus(data);
            }
        } catch (error) {
            console.error('Error fetching pipeline status:', error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, [fetchStatus]);

    const toggleBackend = async (backendId: string, enabled: boolean) => {
        try {
            await fetch(`/api/pipeline/backends/${backendId}/enable`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled }),
            });
            fetchStatus();
        } catch (error) {
            console.error('Error toggling backend:', error);
        }
    };

    const removeBackend = async (backendId: string) => {
        if (!confirm('¿Eliminar este backend?')) return;

        try {
            await fetch(`/api/pipeline/backends/${backendId}`, {
                method: 'DELETE',
            });
            fetchStatus();
        } catch (error) {
            console.error('Error removing backend:', error);
        }
    };

    const addBackend = async () => {
        try {
            await fetch('/api/pipeline/backends', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    backend_type: newBackendType,
                    model_name: newModelName,
                }),
            });
            setShowAddBackend(false);
            setNewModelName('');
            fetchStatus();
        } catch (error) {
            console.error('Error adding backend:', error);
        }
    };

    const updateFusion = async (strategy: string) => {
        try {
            await fetch('/api/pipeline/fusion', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy,
                    min_backends_agree: strategy === 'consensus' ? 2 : 1,
                    iou_threshold: 0.5,
                    confidence_aggregation: 'max',
                }),
            });
            fetchStatus();
        } catch (error) {
            console.error('Error updating fusion:', error);
        }
    };

    if (loading) {
        return (
            <div className={`p-6 bg-slate-900/90 rounded-2xl ${className}`}>
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-slate-700 rounded w-1/3" />
                    <div className="h-32 bg-slate-700 rounded" />
                    <div className="h-24 bg-slate-700 rounded" />
                </div>
            </div>
        );
    }

    return (
        <div className={`p-6 bg-slate-900/90 backdrop-blur-lg rounded-2xl border border-slate-700/50 ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <span className="text-2xl">🧠</span>
                    Argos Pipeline
                </h2>

                {status && (
                    <div className="flex items-center gap-3 text-sm">
                        <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 rounded-full">
                            {status.capabilities.backends_count} backends
                        </span>
                        <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded-full">
                            {status.capabilities.max_fps} FPS max
                        </span>
                    </div>
                )}
            </div>

            {/* Presets Section */}
            <PresetSelector
                onPresetChange={() => fetchStatus()}
                className="mb-8"
            />

            {/* Active Backends */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <span>🔧</span>
                        Backends Activos
                    </h3>
                    <button
                        onClick={() => setShowAddBackend(!showAddBackend)}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors"
                    >
                        + Agregar
                    </button>
                </div>

                {/* Add Backend Form */}
                {showAddBackend && (
                    <div className="mb-4 p-4 bg-slate-800/70 rounded-xl border border-slate-600/50">
                        <div className="flex gap-3 flex-wrap">
                            <select
                                value={newBackendType}
                                onChange={(e) => setNewBackendType(e.target.value)}
                                className="px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600"
                            >
                                {BACKEND_TYPES.map((type) => (
                                    <option key={type.id} value={type.id}>
                                        {type.icon} {type.name}
                                    </option>
                                ))}
                            </select>

                            <input
                                type="text"
                                value={newModelName}
                                onChange={(e) => setNewModelName(e.target.value)}
                                placeholder="Modelo (ej: yolo11n.pt)"
                                className="flex-1 min-w-48 px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 placeholder-slate-400"
                            />

                            <button
                                onClick={addBackend}
                                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
                            >
                                Agregar
                            </button>

                            <button
                                onClick={() => setShowAddBackend(false)}
                                className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white rounded-lg transition-colors"
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>
                )}

                {/* Backend Cards */}
                <div className="space-y-3">
                    {status?.backends.map((backend) => {
                        const typeInfo = BACKEND_TYPES.find(t => t.id === backend.backend_type);

                        return (
                            <div
                                key={backend.backend_id}
                                className={`
                  p-4 rounded-xl border transition-all
                  ${backend.enabled
                                        ? 'bg-slate-800/70 border-slate-600/50'
                                        : 'bg-slate-800/30 border-slate-700/30 opacity-60'
                                    }
                `}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">{typeInfo?.icon || '🔌'}</span>
                                        <div>
                                            <div className="font-medium text-white">
                                                {typeInfo?.name || backend.backend_type}
                                            </div>
                                            <div className="text-sm text-slate-400">
                                                {backend.model_name || 'Modelo por defecto'}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        {/* Capabilities badges */}
                                        <div className="flex gap-1.5">
                                            {backend.capabilities.supports_pose && (
                                                <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded-full">
                                                    Pose
                                                </span>
                                            )}
                                            {backend.capabilities.supports_tracking && (
                                                <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                                                    Tracking
                                                </span>
                                            )}
                                            <span className="px-2 py-0.5 bg-slate-600/50 text-slate-300 text-xs rounded-full">
                                                {backend.capabilities.max_fps} FPS
                                            </span>
                                        </div>

                                        {/* Toggle */}
                                        <button
                                            onClick={() => toggleBackend(backend.backend_id, !backend.enabled)}
                                            className={`
                        w-12 h-6 rounded-full transition-colors relative
                        ${backend.enabled ? 'bg-emerald-500' : 'bg-slate-600'}
                      `}
                                        >
                                            <div className={`
                        absolute top-1 w-4 h-4 bg-white rounded-full transition-transform
                        ${backend.enabled ? 'left-7' : 'left-1'}
                      `} />
                                        </button>

                                        {/* Remove */}
                                        <button
                                            onClick={() => removeBackend(backend.backend_id)}
                                            className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}

                    {status?.backends.length === 0 && (
                        <div className="text-center py-8 text-slate-400">
                            No hay backends configurados. Selecciona un preset o agrega uno manualmente.
                        </div>
                    )}
                </div>
            </div>

            {/* Fusion Strategy */}
            <div>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <span>🔀</span>
                    Estrategia de Fusión
                </h3>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                    {FUSION_STRATEGIES.map((strategy) => {
                        const isActive = status?.fusion.strategy === strategy.id;

                        return (
                            <button
                                key={strategy.id}
                                onClick={() => updateFusion(strategy.id)}
                                disabled={status?.backends.length === 0}
                                className={`
                  p-3 rounded-xl text-center transition-all
                  ${isActive
                                        ? 'bg-blue-600 text-white ring-2 ring-blue-400/50'
                                        : 'bg-slate-800/70 text-slate-300 hover:bg-slate-700/70'
                                    }
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
                            >
                                <div className="text-xl mb-1">{strategy.icon}</div>
                                <div className="text-xs font-medium">{strategy.name}</div>
                            </button>
                        );
                    })}
                </div>

                {status?.fusion && (
                    <p className="mt-3 text-sm text-slate-400">
                        {FUSION_STRATEGIES.find(s => s.id === status.fusion.strategy)?.description}
                    </p>
                )}
            </div>
        </div>
    );
};

export default PipelinePanel;

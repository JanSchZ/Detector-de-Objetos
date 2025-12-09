'use client';

import React, { useState, useEffect } from 'react';

interface Preset {
    id: string;
    name: string;
    description: string;
    icon: string;
    backends: { type: string; model: string }[];
    features: Record<string, boolean>;
}

interface PresetSelectorProps {
    onPresetChange?: (presetId: string) => void;
    className?: string;
}

const PresetSelector: React.FC<PresetSelectorProps> = ({
    onPresetChange,
    className = ''
}) => {
    const [presets, setPresets] = useState<Preset[]>([]);
    const [activePreset, setActivePreset] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [applying, setApplying] = useState<string | null>(null);

    useEffect(() => {
        fetchPresets();
        fetchStatus();
    }, []);

    const fetchPresets = async () => {
        try {
            const response = await fetch('/api/pipeline/presets');
            if (response.ok) {
                const data = await response.json();
                setPresets(data);
            }
        } catch (error) {
            console.error('Error fetching presets:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchStatus = async () => {
        try {
            const response = await fetch('/api/pipeline/status');
            if (response.ok) {
                const data = await response.json();
                setActivePreset(data.active_preset);
            }
        } catch (error) {
            console.error('Error fetching status:', error);
        }
    };

    const applyPreset = async (presetId: string) => {
        setApplying(presetId);
        try {
            const response = await fetch(`/api/pipeline/presets/${presetId}/apply`, {
                method: 'POST',
            });

            if (response.ok) {
                setActivePreset(presetId);
                onPresetChange?.(presetId);
            }
        } catch (error) {
            console.error('Error applying preset:', error);
        } finally {
            setApplying(null);
        }
    };

    const getPresetColor = (presetId: string): string => {
        const colors: Record<string, string> = {
            home_security: 'from-blue-500 to-blue-600',
            pet_monitor: 'from-amber-500 to-orange-500',
            high_precision: 'from-emerald-500 to-green-600',
            lab_research: 'from-purple-500 to-violet-600',
            wildlife: 'from-lime-500 to-green-500',
            industrial: 'from-slate-500 to-gray-600',
            custom: 'from-zinc-600 to-zinc-700',
        };
        return colors[presetId] || 'from-slate-500 to-slate-600';
    };

    if (loading) {
        return (
            <div className={`animate-pulse ${className}`}>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="h-24 bg-slate-700 rounded-xl" />
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className={className}>
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">🎯</span>
                Presets de Detección
            </h3>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {presets.map((preset) => {
                    const isActive = activePreset === preset.id;
                    const isApplying = applying === preset.id;

                    return (
                        <button
                            key={preset.id}
                            onClick={() => applyPreset(preset.id)}
                            disabled={isApplying || isActive}
                            className={`
                relative p-4 rounded-xl text-left transition-all duration-200
                ${isActive
                                    ? `bg-gradient-to-br ${getPresetColor(preset.id)} ring-2 ring-white/30 shadow-lg`
                                    : 'bg-slate-800/70 hover:bg-slate-700/70 hover:scale-[1.02]'
                                }
                ${isApplying ? 'opacity-70 cursor-wait' : ''}
                disabled:cursor-default
              `}
                        >
                            {isActive && (
                                <div className="absolute top-2 right-2">
                                    <span className="flex h-2 w-2">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
                                    </span>
                                </div>
                            )}

                            <div className="text-3xl mb-2">{preset.icon}</div>
                            <div className="font-medium text-white text-sm truncate">
                                {preset.name.replace(/^[^\s]+\s/, '')}
                            </div>
                            <div className="text-xs text-white/60 mt-1 line-clamp-2">
                                {preset.description}
                            </div>

                            {isApplying && (
                                <div className="absolute inset-0 flex items-center justify-center bg-black/30 rounded-xl">
                                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                </div>
                            )}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default PresetSelector;

'use client';

import { useState, useEffect } from 'react';
import {
    getAnalyticsSummary,
    getDetectionTrends,
    getHeatmapData,
    AnalyticsSummary,
    DetectionTrends,
    HeatmapData,
} from '@/lib/api';

interface AnalyticsDashboardProps {
    onClose?: () => void;
}

export default function AnalyticsDashboard({ onClose }: AnalyticsDashboardProps) {
    const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
    const [trends, setTrends] = useState<DetectionTrends | null>(null);
    const [heatmap, setHeatmap] = useState<HeatmapData | null>(null);
    const [period, setPeriod] = useState<'day' | 'week' | 'month'>('week');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadData();
    }, [period]);

    const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [summaryData, trendsData, heatmapData] = await Promise.all([
                getAnalyticsSummary(period === 'day' ? 1 : period === 'week' ? 7 : 30),
                getDetectionTrends(period),
                getHeatmapData(),
            ]);
            setSummary(summaryData);
            setTrends(trendsData);
            setHeatmap(heatmapData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error cargando analytics');
        } finally {
            setLoading(false);
        }
    };

    const getMaxHeatmapValue = () => {
        if (!heatmap) return 1;
        return Math.max(...heatmap.heatmap.flat(), 1);
    };

    const getHeatmapColor = (value: number) => {
        const max = getMaxHeatmapValue();
        const intensity = value / max;
        if (intensity === 0) return 'bg-secondary';
        if (intensity < 0.25) return 'bg-amber-900/30';
        if (intensity < 0.5) return 'bg-amber-700/50';
        if (intensity < 0.75) return 'bg-amber-500/70';
        return 'bg-amber-400';
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
                <div className="flex items-center gap-3">
                    <span className="text-xl">📊</span>
                    <h2 className="text-lg font-semibold text-foreground">Analytics</h2>
                </div>
                <div className="flex items-center gap-2">
                    {/* Period Selector */}
                    <div className="flex bg-secondary rounded-md p-0.5">
                        {(['day', 'week', 'month'] as const).map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${period === p
                                        ? 'bg-primary text-primary-foreground'
                                        : 'text-muted-foreground hover:text-foreground'
                                    }`}
                            >
                                {p === 'day' ? 'Hoy' : p === 'week' ? 'Semana' : 'Mes'}
                            </button>
                        ))}
                    </div>
                    {onClose && (
                        <button onClick={onClose} className="btn-ghost p-2 rounded-md">
                            ✕
                        </button>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {loading ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="animate-pulse text-muted-foreground">Cargando...</div>
                    </div>
                ) : error ? (
                    <div className="bg-destructive/10 text-destructive p-4 rounded-md">
                        {error}
                    </div>
                ) : (
                    <>
                        {/* Summary Cards */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                            <div className="card">
                                <div className="label mb-1">Detecciones Hoy</div>
                                <div className="text-2xl font-bold text-primary">
                                    {summary?.today.total_detections || 0}
                                </div>
                            </div>
                            <div className="card">
                                <div className="label mb-1">Alertas ({period})</div>
                                <div className="text-2xl font-bold text-destructive">
                                    {summary?.alerts.total || 0}
                                </div>
                            </div>
                            <div className="card">
                                <div className="label mb-1">Hora Pico</div>
                                <div className="text-2xl font-bold text-foreground">
                                    {summary?.today.peak_hour || 0}:00
                                </div>
                            </div>
                            <div className="card">
                                <div className="label mb-1">Total Período</div>
                                <div className="text-2xl font-bold text-foreground">
                                    {trends?.total || 0}
                                </div>
                            </div>
                        </div>

                        {/* Trend Chart (simplified bar chart) */}
                        <div className="card">
                            <div className="label mb-3">Tendencia de Detecciones</div>
                            {trends && trends.trend.length > 0 ? (
                                <div className="flex items-end gap-1 h-32">
                                    {trends.trend.map((d, i) => {
                                        const maxCount = Math.max(...trends.trend.map((t) => t.count), 1);
                                        const height = (d.count / maxCount) * 100;
                                        return (
                                            <div
                                                key={i}
                                                className="flex-1 flex flex-col items-center gap-1"
                                            >
                                                <div
                                                    className="w-full bg-primary/80 rounded-t transition-all duration-300 hover:bg-primary"
                                                    style={{ height: `${height}%`, minHeight: d.count > 0 ? '4px' : 0 }}
                                                    title={`${d.date}: ${d.count}`}
                                                />
                                                <span className="text-[9px] text-muted-foreground truncate max-w-full">
                                                    {d.date.slice(-5)}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="text-center text-muted-foreground py-8">
                                    Sin datos para este período
                                </div>
                            )}
                        </div>

                        {/* Class Distribution */}
                        {summary && Object.keys(summary.today.class_counts).length > 0 && (
                            <div className="card">
                                <div className="label mb-3">Clases Detectadas Hoy</div>
                                <div className="flex flex-wrap gap-2">
                                    {Object.entries(summary.today.class_counts)
                                        .sort(([, a], [, b]) => b - a)
                                        .slice(0, 10)
                                        .map(([className, count]) => (
                                            <div key={className} className="chip">
                                                {className}: <span className="font-semibold text-foreground ml-1">{count}</span>
                                            </div>
                                        ))}
                                </div>
                            </div>
                        )}

                        {/* Heatmap */}
                        {heatmap && (
                            <div className="card">
                                <div className="label mb-3">Mapa de Actividad (últimos 30 días)</div>
                                <div className="overflow-x-auto">
                                    <div className="min-w-[600px]">
                                        {/* Hours header */}
                                        <div className="flex mb-1 ml-12">
                                            {[0, 3, 6, 9, 12, 15, 18, 21].map((h) => (
                                                <div
                                                    key={h}
                                                    className="text-[9px] text-muted-foreground"
                                                    style={{ width: '12.5%' }}
                                                >
                                                    {h}:00
                                                </div>
                                            ))}
                                        </div>
                                        {/* Grid */}
                                        {heatmap.heatmap.map((dayData, dayIdx) => (
                                            <div key={dayIdx} className="flex items-center gap-1 mb-0.5">
                                                <div className="w-10 text-[10px] text-muted-foreground">
                                                    {heatmap.days[dayIdx]}
                                                </div>
                                                <div className="flex-1 flex gap-px">
                                                    {dayData.map((value, hourIdx) => (
                                                        <div
                                                            key={hourIdx}
                                                            className={`flex-1 h-4 rounded-sm ${getHeatmapColor(value)} transition-colors`}
                                                            title={`${heatmap.days[dayIdx]} ${hourIdx}:00 - ${value} eventos`}
                                                        />
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                {/* Legend */}
                                <div className="flex items-center gap-2 mt-3 text-[10px] text-muted-foreground">
                                    <span>Menos</span>
                                    <div className="w-4 h-3 bg-secondary rounded-sm" />
                                    <div className="w-4 h-3 bg-amber-900/30 rounded-sm" />
                                    <div className="w-4 h-3 bg-amber-700/50 rounded-sm" />
                                    <div className="w-4 h-3 bg-amber-500/70 rounded-sm" />
                                    <div className="w-4 h-3 bg-amber-400 rounded-sm" />
                                    <span>Más</span>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}

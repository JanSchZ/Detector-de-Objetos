'use client';

import { TrackedObject } from '@/lib/api';

interface AnalyticsPanelProps {
    objects: TrackedObject[];
    counts: Record<string, number>;
    sessionStart: number | null;
    isConnected: boolean;
}

/**
 * Analytics panel with stats and export functionality
 */
export function AnalyticsPanel({ objects, counts, sessionStart, isConnected }: AnalyticsPanelProps) {
    const sessionDuration = sessionStart
        ? Math.floor((Date.now() - sessionStart) / 1000)
        : 0;

    const formatDuration = (seconds: number) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    };

    const totalDetections = Object.values(counts).reduce((a, b) => a + b, 0);
    const sortedCounts = Object.entries(counts).sort(([, a], [, b]) => b - a);

    const handleExportJSON = () => {
        const data = {
            timestamp: new Date().toISOString(),
            sessionDuration,
            totalDetections,
            counts,
            currentObjects: objects,
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `visionmind-export-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleExportCSV = () => {
        const headers = ['class_name', 'count'];
        const rows = sortedCounts.map(([name, count]) => `${name},${count}`);
        const csv = [headers.join(','), ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `visionmind-counts-${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="space-y-5">
            {/* Session Info */}
            <section>
                <h3 className="label mb-3">Sesión</h3>
                <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 rounded bg-secondary border border-border">
                        <div className="text-xs text-muted-foreground mb-1">Estado</div>
                        <div className={`text-sm font-medium ${isConnected ? 'text-primary' : 'text-muted-foreground'}`}>
                            {isConnected ? 'Activa' : 'Inactiva'}
                        </div>
                    </div>
                    <div className="p-3 rounded bg-secondary border border-border">
                        <div className="text-xs text-muted-foreground mb-1">Duración</div>
                        <div className="text-sm font-mono">{formatDuration(sessionDuration)}</div>
                    </div>
                </div>
            </section>

            {/* Detection Stats */}
            <section>
                <h3 className="label mb-3">Detecciones Totales</h3>
                <div className="p-3 rounded bg-secondary border border-border mb-3">
                    <div className="text-2xl font-bold text-primary">{totalDetections}</div>
                    <div className="text-xs text-muted-foreground">objetos detectados</div>
                </div>

                {sortedCounts.length > 0 && (
                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                        {sortedCounts.map(([className, count]) => (
                            <div
                                key={className}
                                className="flex items-center justify-between py-1.5 px-2 rounded bg-muted/50"
                            >
                                <span className="text-sm capitalize">{className}</span>
                                <span className="text-sm font-mono text-primary">{count}</span>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Export */}
            <section>
                <h3 className="label mb-3">Exportar Datos</h3>
                <div className="flex gap-2">
                    <button onClick={handleExportJSON} className="btn btn-secondary flex-1 text-xs">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        JSON
                    </button>
                    <button onClick={handleExportCSV} className="btn btn-secondary flex-1 text-xs">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        CSV
                    </button>
                </div>
            </section>
        </div>
    );
}

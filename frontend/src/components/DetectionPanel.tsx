'use client';

import { TrackedObject } from '@/lib/api';

interface DetectionPanelProps {
    objects: TrackedObject[];
    inferenceTime: number;
}

/**
 * Panel showing tracked objects with confidence bars and IDs
 */
export function DetectionPanel({ objects, inferenceTime }: DetectionPanelProps) {
    // Group by class for cleaner display
    const grouped = objects.reduce((acc, obj) => {
        const key = obj.class_name_es;
        if (!acc[key]) acc[key] = [];
        acc[key].push(obj);
        return acc;
    }, {} as Record<string, TrackedObject[]>);

    const sortedGroups = Object.entries(grouped).sort(([, a], [, b]) => b.length - a.length);

    return (
        <div className="card h-full flex flex-col">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Detecciones</h3>
                <span className="text-xs text-muted-foreground">{inferenceTime.toFixed(1)}ms</span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
                {sortedGroups.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">
                        No se han detectado objetos
                    </p>
                ) : (
                    sortedGroups.map(([className, items]) => (
                        <div
                            key={className}
                            className="detection-item p-3 rounded-lg bg-secondary/50 border border-border/50"
                        >
                            <div className="flex items-center justify-between mb-2">
                                <span className="font-medium capitalize">{className}</span>
                                <span className="px-2 py-0.5 rounded-full bg-primary/20 text-primary text-xs font-semibold">
                                    {items.length}
                                </span>
                            </div>

                            <div className="space-y-1.5">
                                {items.slice(0, 3).map((obj) => (
                                    <div key={obj.tracker_id} className="flex items-center gap-2">
                                        <span className="text-xs text-muted-foreground min-w-[32px]">
                                            #{obj.tracker_id}
                                        </span>
                                        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                                            <div
                                                className="h-full rounded-full transition-all duration-300"
                                                style={{
                                                    width: `${obj.confidence * 100}%`,
                                                    background: getConfidenceGradient(obj.confidence),
                                                }}
                                            />
                                        </div>
                                        <span className="text-xs text-muted-foreground min-w-[32px] text-right">
                                            {(obj.confidence * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                ))}
                                {items.length > 3 && (
                                    <p className="text-xs text-muted-foreground">+{items.length - 3} más</p>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

function getConfidenceGradient(confidence: number): string {
    if (confidence >= 0.8) {
        return 'linear-gradient(90deg, #10b981 0%, #22d3ee 100%)';
    } else if (confidence >= 0.5) {
        return 'linear-gradient(90deg, #f59e0b 0%, #10b981 100%)';
    } else {
        return 'linear-gradient(90deg, #ef4444 0%, #f59e0b 100%)';
    }
}

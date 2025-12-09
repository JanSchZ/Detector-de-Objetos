'use client';

import { ConnectionStatus } from '@/hooks/useDetections';

interface StatsBarProps {
    status: ConnectionStatus;
    fps: number;
    inferenceTime: number;
    totalObjects: number;
    streamStatus?: string | null;
}

/**
 * Horizontal stats bar showing connection status, FPS, inference time, etc.
 */
export function StatsBar({ status, fps, inferenceTime, totalObjects, streamStatus }: StatsBarProps) {
    return (
        <div className="flex flex-wrap items-center gap-4 p-4 rounded-xl bg-card border border-border">
            {/* Connection Status */}
            <div className="flex items-center gap-2">
                <div className={`status-badge ${status === 'connected' ? 'connected' : 'disconnected'}`}>
                    <span className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-primary' :
                            status === 'connecting' ? 'bg-yellow-500' :
                                'bg-destructive'
                        }`} />
                    {status === 'connected' ? 'Conectado' :
                        status === 'connecting' ? 'Conectando...' :
                            status === 'error' ? 'Error' : 'Desconectado'}
                </div>
            </div>

            <div className="h-6 w-px bg-border" />

            {/* Stats */}
            <div className="flex items-center gap-6">
                <StatItem label="FPS" value={fps} unit="" highlight />
                <StatItem label="Inferencia" value={inferenceTime.toFixed(1)} unit="ms" />
                <StatItem label="Objetos" value={totalObjects} unit="" />
                {streamStatus && <StatItem label="Stream" value={streamStatus} unit="" />}
            </div>
        </div>
    );
}

interface StatItemProps {
    label: string;
    value: number | string;
    unit: string;
    highlight?: boolean;
}

function StatItem({ label, value, unit, highlight }: StatItemProps) {
    return (
        <div className="flex items-baseline gap-1.5">
            <span className="text-xs text-muted-foreground">{label}:</span>
            <span className={`font-semibold tabular-nums ${highlight ? 'text-primary' : ''}`}>
                {value}
            </span>
            {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
        </div>
    );
}

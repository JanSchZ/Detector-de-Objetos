'use client';

import { useState } from 'react';

interface QuickStatsProps {
    counts: Record<string, number>;
    zoneAlerts: { warning: number; danger: number };
    isConnected: boolean;
}

/**
 * Collapsible floating stats panel
 */
export function QuickStats({ counts, zoneAlerts, isConnected }: QuickStatsProps) {
    const [isExpanded, setIsExpanded] = useState(true);

    if (!isConnected) return null;

    const totalObjects = Object.values(counts).reduce((a, b) => a + b, 0);
    const topClasses = Object.entries(counts)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 4);

    return (
        <div className="bg-card/90 backdrop-blur-sm border border-border rounded-lg overflow-hidden">
            {/* Header - always visible */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-secondary/50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium">{totalObjects} objetos</span>
                    {(zoneAlerts.warning > 0 || zoneAlerts.danger > 0) && (
                        <span className="flex items-center gap-1 text-xs">
                            {zoneAlerts.warning > 0 && (
                                <span className="text-warning">⚠ {zoneAlerts.warning}</span>
                            )}
                            {zoneAlerts.danger > 0 && (
                                <span className="text-destructive">🔴 {zoneAlerts.danger}</span>
                            )}
                        </span>
                    )}
                </div>
                <svg
                    className={`w-3.5 h-3.5 text-muted-foreground transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {/* Expanded content */}
            {isExpanded && topClasses.length > 0 && (
                <div className="px-3 pb-2 border-t border-border/50">
                    <div className="flex flex-wrap gap-1.5 pt-2">
                        {topClasses.map(([className, count]) => (
                            <span key={className} className="chip">
                                <span className="capitalize">{className}</span>
                                <span className="text-primary font-medium">{count}</span>
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

'use client';

import { useEffect, useState } from 'react';

interface Alert {
    id: string;
    title: string;
    message: string;
    priority: string;
    zone_type: 'warning' | 'danger';
    class_name: string;
    timestamp: number;
}

interface AlertBannerProps {
    alerts: Alert[];
}

/**
 * Alert banner that appears when danger/warning events occur
 */
export function AlertBanner({ alerts }: AlertBannerProps) {
    const [visible, setVisible] = useState(false);
    const [currentAlert, setCurrentAlert] = useState<Alert | null>(null);

    useEffect(() => {
        if (alerts.length > 0) {
            // Show most recent alert
            const latest = alerts[alerts.length - 1];
            setCurrentAlert(latest);
            setVisible(true);

            // Auto-hide after 5 seconds for warnings, 10 for dangers
            const timeout = latest.zone_type === 'danger' ? 10000 : 5000;
            const timer = setTimeout(() => setVisible(false), timeout);

            return () => clearTimeout(timer);
        }
    }, [alerts]);

    if (!visible || !currentAlert) return null;

    const isDanger = currentAlert.zone_type === 'danger';

    return (
        <div
            className={`fixed top-0 left-0 right-0 z-50 p-4 ${isDanger
                    ? 'bg-gradient-to-r from-red-600 to-red-500 animate-pulse'
                    : 'bg-gradient-to-r from-amber-500 to-orange-500'
                }`}
        >
            <div className="max-w-4xl mx-auto flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <span className="text-4xl">{isDanger ? '🚨' : '⚠️'}</span>
                    <div>
                        <h2 className="text-xl font-bold text-white">{currentAlert.title}</h2>
                        <p className="text-white/90">{currentAlert.message}</p>
                    </div>
                </div>
                <button
                    onClick={() => setVisible(false)}
                    className="text-white/80 hover:text-white text-2xl px-3"
                >
                    ×
                </button>
            </div>
        </div>
    );
}

/**
 * Compact alert list for sidebar
 */
export function AlertList({ alerts }: { alerts: Alert[] }) {
    if (alerts.length === 0) {
        return (
            <div className="text-center text-muted-foreground py-4 text-sm">
                Sin alertas recientes
            </div>
        );
    }

    return (
        <div className="space-y-2 max-h-60 overflow-y-auto">
            {alerts.slice(-5).reverse().map((alert) => (
                <div
                    key={alert.id}
                    className={`p-3 rounded-lg border ${alert.zone_type === 'danger'
                            ? 'bg-red-500/10 border-red-500/30'
                            : 'bg-amber-500/10 border-amber-500/30'
                        }`}
                >
                    <div className="flex items-start gap-2">
                        <span>{alert.zone_type === 'danger' ? '🚨' : '⚠️'}</span>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{alert.message}</p>
                            <p className="text-xs text-muted-foreground">
                                {new Date(alert.timestamp * 1000).toLocaleTimeString()}
                            </p>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    );
}

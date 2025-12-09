'use client';

interface ObjectCounterProps {
    counts: Record<string, number>;
    total: number;
}

/**
 * Grid display of object counts by class
 */
export function ObjectCounter({ counts, total }: ObjectCounterProps) {
    const sortedCounts = Object.entries(counts).sort(([, a], [, b]) => b - a);

    return (
        <div className="card">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Contador</h3>
                <div className="flex items-center gap-2">
                    <span className="text-2xl font-bold gradient-text counter-value">
                        {total}
                    </span>
                    <span className="text-xs text-muted-foreground">objetos</span>
                </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {sortedCounts.length === 0 ? (
                    <p className="col-span-full text-sm text-muted-foreground text-center py-4">
                        Sin objetos detectados
                    </p>
                ) : (
                    sortedCounts.map(([className, count]) => (
                        <div
                            key={className}
                            className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/50 border border-border/50 counter-value"
                        >
                            <span className="text-sm capitalize truncate mr-2">{className}</span>
                            <span className="text-lg font-bold text-primary">{count}</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

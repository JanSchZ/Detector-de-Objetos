'use client';

interface OverlayTogglesProps {
    options: {
        id: string;
        label: string;
        enabled: boolean;
    }[];
    onToggle: (id: string) => void;
}

/**
 * Floating toggle buttons for visual overlays
 */
export function OverlayToggles({ options, onToggle }: OverlayTogglesProps) {
    return (
        <div className="flex flex-wrap gap-1.5">
            {options.map((option) => (
                <button
                    key={option.id}
                    onClick={() => onToggle(option.id)}
                    className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${option.enabled
                            ? 'bg-primary/20 text-primary border border-primary/30'
                            : 'bg-secondary/80 text-muted-foreground border border-border hover:bg-secondary'
                        }`}
                >
                    {option.label}
                </button>
            ))}
        </div>
    );
}

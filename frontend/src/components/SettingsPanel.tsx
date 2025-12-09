'use client';

interface SettingsPanelProps {
    // Detection settings
    confidenceThreshold: number;
    onConfidenceChange: (value: number) => void;
    iouThreshold: number;
    onIouChange: (value: number) => void;
    maxFps: number;
    onMaxFpsChange: (value: number) => void;

    // Overlay settings
    overlays: {
        boxes: boolean;
        labels: boolean;
        confidence: boolean;
        trackerIds: boolean;
        zones: boolean;
        trails: boolean;
    };
    onOverlayChange: (key: keyof SettingsPanelProps['overlays'], value: boolean) => void;

    // Colors
    boxColor: string;
    onBoxColorChange: (color: string) => void;
}

/**
 * Settings panel for detection parameters and visual overlays
 */
export function SettingsPanel({
    confidenceThreshold,
    onConfidenceChange,
    iouThreshold,
    onIouChange,
    maxFps,
    onMaxFpsChange,
    overlays,
    onOverlayChange,
    boxColor,
    onBoxColorChange,
}: SettingsPanelProps) {
    const overlayOptions = [
        { key: 'boxes' as const, label: 'Bounding Boxes', icon: '▢' },
        { key: 'labels' as const, label: 'Etiquetas de clase', icon: 'Aa' },
        { key: 'confidence' as const, label: '% Confianza', icon: '%' },
        { key: 'trackerIds' as const, label: 'Tracker IDs', icon: '#' },
        { key: 'zones' as const, label: 'Zonas', icon: '◇' },
        { key: 'trails' as const, label: 'Trayectorias', icon: '~' },
    ];

    return (
        <div className="space-y-5">
            {/* Detection Parameters */}
            <section>
                <h3 className="label mb-3">Parámetros de Detección</h3>
                <div className="space-y-4">
                    <div>
                        <div className="flex justify-between mb-1.5">
                            <label className="text-xs text-muted-foreground">Umbral de Confianza</label>
                            <span className="text-xs font-mono text-primary">{(confidenceThreshold * 100).toFixed(0)}%</span>
                        </div>
                        <input
                            type="range"
                            min={0}
                            max={100}
                            value={confidenceThreshold * 100}
                            onChange={(e) => onConfidenceChange(parseInt(e.target.value) / 100)}
                            className="slider w-full"
                        />
                    </div>

                    <div>
                        <div className="flex justify-between mb-1.5">
                            <label className="text-xs text-muted-foreground">IOU Threshold</label>
                            <span className="text-xs font-mono">{(iouThreshold * 100).toFixed(0)}%</span>
                        </div>
                        <input
                            type="range"
                            min={0}
                            max={100}
                            value={iouThreshold * 100}
                            onChange={(e) => onIouChange(parseInt(e.target.value) / 100)}
                            className="slider w-full"
                        />
                    </div>

                    <div>
                        <div className="flex justify-between mb-1.5">
                            <label className="text-xs text-muted-foreground">FPS Máximo</label>
                            <span className="text-xs font-mono">{maxFps}</span>
                        </div>
                        <input
                            type="range"
                            min={5}
                            max={60}
                            value={maxFps}
                            onChange={(e) => onMaxFpsChange(parseInt(e.target.value))}
                            className="slider w-full"
                        />
                    </div>
                </div>
            </section>

            {/* Visual Overlays */}
            <section>
                <h3 className="label mb-3">Overlays Visuales</h3>
                <div className="space-y-1">
                    {overlayOptions.map((option) => (
                        <label
                            key={option.key}
                            className="flex items-center justify-between py-2 px-2 rounded hover:bg-secondary cursor-pointer"
                        >
                            <div className="flex items-center gap-2">
                                <span className="w-5 text-center text-xs text-muted-foreground">{option.icon}</span>
                                <span className="text-sm">{option.label}</span>
                            </div>
                            <div className="relative">
                                <input
                                    type="checkbox"
                                    checked={overlays[option.key]}
                                    onChange={(e) => onOverlayChange(option.key, e.target.checked)}
                                    className="sr-only peer"
                                />
                                <div className="w-9 h-5 bg-secondary rounded-full peer peer-checked:bg-primary/30 transition-colors" />
                                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-muted-foreground rounded-full peer-checked:translate-x-4 peer-checked:bg-primary transition-all" />
                            </div>
                        </label>
                    ))}
                </div>
            </section>

            {/* Colors */}
            <section>
                <h3 className="label mb-3">Colores</h3>
                <div className="flex items-center gap-3">
                    <label className="text-xs text-muted-foreground">Color de cajas</label>
                    <div className="flex items-center gap-2">
                        <input
                            type="color"
                            value={boxColor}
                            onChange={(e) => onBoxColorChange(e.target.value)}
                            className="w-8 h-8 rounded cursor-pointer border border-border bg-transparent"
                        />
                        <span className="text-xs font-mono text-muted-foreground">{boxColor}</span>
                    </div>
                </div>
            </section>
        </div>
    );
}

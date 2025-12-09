'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

export interface Zone {
    id: string;
    name: string;
    type: 'warning' | 'danger';
    polygon: [number, number][];
    color: string;
    enabled: boolean;
}

interface ZoneEditorProps {
    zones: Zone[];
    frameSize: { width: number; height: number } | null;
    onZoneCreate: (zone: Zone) => void;
    onZoneDelete: (zoneId: string) => void;
    onZoneUpdate?: (zone: Zone) => void;
    isEditing: boolean;
    onEditingChange: (editing: boolean) => void;
    selectedZoneId?: string | null;
    onSelectZone?: (zoneId: string | null) => void;
}

/**
 * Zone editor overlay for drawing polygons on video
 * IMPORTANT: This component handles its own click events via a transparent overlay
 */
export function ZoneEditor({
    zones,
    frameSize,
    onZoneCreate,
    onZoneDelete,
    onZoneUpdate,
    isEditing,
    onEditingChange,
    selectedZoneId,
    onSelectZone,
}: ZoneEditorProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [currentPoints, setCurrentPoints] = useState<[number, number][]>([]);
    const [zoneType, setZoneType] = useState<'warning' | 'danger'>('warning');
    const [zoneName, setZoneName] = useState('');
    const [showForm, setShowForm] = useState(false);
    const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);

    // Get normalized coordinates from mouse event
    const getCoordinates = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        const container = containerRef.current;
        if (!container) return null;

        const rect = container.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        return { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) };
    }, []);

    // Check if point is inside polygon (ray casting)
    const isPointInPolygon = useCallback((px: number, py: number, polygon: [number, number][]) => {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i][0], yi = polygon[i][1];
            const xj = polygon[j][0], yj = polygon[j][1];
            if (((yi > py) !== (yj > py)) && (px < (xj - xi) * (py - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }
        return inside;
    }, []);

    // Find zone at position
    const findZoneAtPosition = useCallback((x: number, y: number): Zone | null => {
        for (let i = zones.length - 1; i >= 0; i--) {
            const zone = zones[i];
            if (zone.enabled && isPointInPolygon(x, y, zone.polygon)) {
                return zone;
            }
        }
        return null;
    }, [zones, isPointInPolygon]);

    // Handle click on overlay
    const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();

        const coords = getCoordinates(e);
        if (!coords) return;

        if (isEditing) {
            // Drawing mode - add point
            // Check if clicking near first point to close polygon
            if (currentPoints.length >= 3) {
                const firstPoint = currentPoints[0];
                const container = containerRef.current;
                if (container) {
                    const rect = container.getBoundingClientRect();
                    const distance = Math.sqrt(
                        Math.pow((coords.x - firstPoint[0]) * rect.width, 2) +
                        Math.pow((coords.y - firstPoint[1]) * rect.height, 2)
                    );
                    if (distance < 20) {
                        // Close polygon and show form
                        setShowForm(true);
                        return;
                    }
                }
            }

            // Add new point
            setCurrentPoints(prev => [...prev, [coords.x, coords.y]]);
        } else if (onSelectZone) {
            // Selection mode
            const zone = findZoneAtPosition(coords.x, coords.y);
            onSelectZone(zone?.id || null);
        }
    }, [isEditing, currentPoints, getCoordinates, findZoneAtPosition, onSelectZone]);

    // Handle mouse move
    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        if (isEditing) return;

        const coords = getCoordinates(e);
        if (!coords) return;

        const zone = findZoneAtPosition(coords.x, coords.y);
        setHoveredZoneId(zone?.id || null);
    }, [isEditing, getCoordinates, findZoneAtPosition]);

    // Draw on canvas
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !frameSize) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        canvas.width = frameSize.width;
        canvas.height = frameSize.height;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw existing zones
        zones.forEach((zone) => {
            if (!zone.enabled) return;

            const points = zone.polygon.map(([x, y]) => [
                x * canvas.width,
                y * canvas.height,
            ]);

            if (points.length < 3) return;

            const isSelected = zone.id === selectedZoneId;
            const isHovered = zone.id === hoveredZoneId;

            // Draw polygon fill
            ctx.beginPath();
            ctx.moveTo(points[0][0], points[0][1]);
            points.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
            ctx.closePath();

            const opacity = isSelected ? '50' : isHovered ? '40' : '25';
            ctx.fillStyle = zone.color + opacity;
            ctx.fill();

            // Draw stroke
            ctx.strokeStyle = zone.color;
            ctx.lineWidth = isSelected ? 3 : 2;
            ctx.stroke();

            // Draw vertices for selected
            if (isSelected) {
                points.forEach(([x, y]) => {
                    ctx.beginPath();
                    ctx.arc(x, y, 5, 0, Math.PI * 2);
                    ctx.fillStyle = '#fff';
                    ctx.fill();
                    ctx.strokeStyle = zone.color;
                    ctx.lineWidth = 2;
                    ctx.stroke();
                });
            }

            // Label
            const labelY = Math.min(...points.map(p => p[1])) - 10;
            const labelX = points[0][0];
            const emoji = zone.type === 'danger' ? '🚨' : '⚠️';

            ctx.font = '12px sans-serif';
            const text = `${emoji} ${zone.name}`;
            const metrics = ctx.measureText(text);

            ctx.fillStyle = 'rgba(0,0,0,0.7)';
            ctx.fillRect(labelX - 4, labelY - 14, metrics.width + 8, 18);

            ctx.fillStyle = '#fff';
            ctx.fillText(text, labelX, labelY);
        });

        // Draw current polygon being created
        if (currentPoints.length > 0 && isEditing) {
            const color = zoneType === 'danger' ? '#ef4444' : '#f59e0b';

            // Draw lines
            ctx.beginPath();
            ctx.moveTo(currentPoints[0][0] * canvas.width, currentPoints[0][1] * canvas.height);
            currentPoints.slice(1).forEach(([x, y]) => {
                ctx.lineTo(x * canvas.width, y * canvas.height);
            });
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.setLineDash([8, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            // Draw closing preview line
            if (currentPoints.length >= 3) {
                ctx.beginPath();
                ctx.moveTo(
                    currentPoints[currentPoints.length - 1][0] * canvas.width,
                    currentPoints[currentPoints.length - 1][1] * canvas.height
                );
                ctx.lineTo(
                    currentPoints[0][0] * canvas.width,
                    currentPoints[0][1] * canvas.height
                );
                ctx.strokeStyle = color + '60';
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 4]);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // Draw points
            currentPoints.forEach(([x, y], index) => {
                ctx.beginPath();
                ctx.arc(x * canvas.width, y * canvas.height, index === 0 ? 10 : 6, 0, Math.PI * 2);
                ctx.fillStyle = index === 0 ? '#22c55e' : color;
                ctx.fill();
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2;
                ctx.stroke();

                // "Click to close" indicator on first point
                if (index === 0 && currentPoints.length >= 3) {
                    ctx.font = '10px sans-serif';
                    ctx.fillStyle = '#fff';
                    ctx.fillText('cerrar', x * canvas.width - 10, y * canvas.height - 15);
                }
            });
        }
    }, [zones, currentPoints, frameSize, zoneType, selectedZoneId, hoveredZoneId, isEditing]);

    const handleSave = () => {
        if (!zoneName.trim()) {
            alert('Ingresa un nombre para la zona');
            return;
        }
        if (currentPoints.length < 3) {
            alert('La zona necesita al menos 3 puntos');
            return;
        }

        const zone: Zone = {
            id: `zone-${Date.now()}`,
            name: zoneName,
            type: zoneType,
            polygon: currentPoints,
            color: zoneType === 'danger' ? '#ef4444' : '#f59e0b',
            enabled: true,
        };

        onZoneCreate(zone);
        setCurrentPoints([]);
        setZoneName('');
        setShowForm(false);
        onEditingChange(false);
    };

    const handleCancel = () => {
        setCurrentPoints([]);
        setZoneName('');
        setShowForm(false);
        onEditingChange(false);
    };

    const handleUndo = () => {
        if (currentPoints.length > 0) {
            setCurrentPoints(prev => prev.slice(0, -1));
        }
    };

    return (
        <>
            {/* Canvas for drawing zones (non-interactive, just visual) */}
            <canvas
                ref={canvasRef}
                className="absolute inset-0 w-full h-full pointer-events-none"
                style={{ zIndex: 5 }}
            />

            {/* Interactive overlay for clicks */}
            <div
                ref={containerRef}
                onClick={handleClick}
                onMouseMove={handleMouseMove}
                onMouseLeave={() => setHoveredZoneId(null)}
                className={`absolute inset-0 ${isEditing
                        ? 'cursor-crosshair z-30'
                        : hoveredZoneId
                            ? 'cursor-pointer z-10'
                            : 'z-10'
                    }`}
                style={{
                    background: isEditing ? 'rgba(0,0,0,0.1)' : 'transparent',
                }}
            />

            {/* Drawing Toolbar */}
            {isEditing && !showForm && (
                <div
                    className="absolute top-4 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-card/95 backdrop-blur-sm px-4 py-3 rounded-xl border border-border shadow-xl"
                    style={{ zIndex: 40 }}
                >
                    <select
                        value={zoneType}
                        onChange={(e) => setZoneType(e.target.value as 'warning' | 'danger')}
                        className="input text-sm py-1.5"
                    >
                        <option value="warning">⚠️ Advertencia</option>
                        <option value="danger">🚨 Peligro</option>
                    </select>

                    <div className="h-6 w-px bg-border" />

                    <span className="text-sm font-medium">
                        {currentPoints.length} punto{currentPoints.length !== 1 ? 's' : ''}
                    </span>

                    {currentPoints.length > 0 && (
                        <button
                            onClick={handleUndo}
                            className="btn btn-secondary text-sm py-1.5 px-3"
                        >
                            ↩ Deshacer
                        </button>
                    )}

                    {currentPoints.length >= 3 && (
                        <button
                            onClick={() => setShowForm(true)}
                            className="btn btn-primary text-sm py-1.5 px-4"
                        >
                            ✓ Guardar zona
                        </button>
                    )}

                    <button
                        onClick={handleCancel}
                        className="btn btn-secondary text-sm py-1.5 px-3"
                    >
                        ✕ Cancelar
                    </button>
                </div>
            )}

            {/* Instructions */}
            {isEditing && currentPoints.length === 0 && !showForm && (
                <div
                    className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-card/95 backdrop-blur-sm px-5 py-3 rounded-xl border border-border shadow-lg"
                    style={{ zIndex: 40 }}
                >
                    <p className="text-sm text-center">
                        <span className="font-medium">Haz clic en la imagen</span> para agregar puntos.
                        <br />
                        <span className="text-muted-foreground">Mínimo 3 puntos. Haz clic en el punto verde para cerrar.</span>
                    </p>
                </div>
            )}

            {/* Zone name form */}
            {showForm && (
                <div
                    className="absolute inset-0 flex items-center justify-center bg-black/70 backdrop-blur-sm"
                    style={{ zIndex: 50 }}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="bg-card rounded-xl border border-border shadow-2xl max-w-md w-full mx-4 p-6">
                        <h3 className="text-xl font-semibold mb-4">Guardar Zona</h3>

                        <div className="flex items-center gap-3 mb-5 p-3 rounded-lg bg-secondary">
                            <div
                                className="w-5 h-5 rounded"
                                style={{ backgroundColor: zoneType === 'danger' ? '#ef4444' : '#f59e0b' }}
                            />
                            <span className="font-medium">
                                {zoneType === 'danger' ? '🚨 Zona de Peligro' : '⚠️ Zona de Advertencia'}
                            </span>
                            <span className="text-muted-foreground ml-auto">
                                {currentPoints.length} puntos
                            </span>
                        </div>

                        <input
                            type="text"
                            value={zoneName}
                            onChange={(e) => setZoneName(e.target.value)}
                            placeholder="Nombre de la zona (ej: Borde Piscina)"
                            className="input w-full mb-5 text-base"
                            autoFocus
                            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                        />

                        <div className="flex gap-3">
                            <button
                                onClick={handleSave}
                                className="btn btn-primary flex-1 py-2.5"
                            >
                                Guardar Zona
                            </button>
                            <button
                                onClick={handleCancel}
                                className="btn btn-secondary py-2.5 px-5"
                            >
                                Cancelar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

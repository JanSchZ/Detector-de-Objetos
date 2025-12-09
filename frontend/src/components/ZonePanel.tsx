'use client';

import { Zone } from './ZoneEditor';

interface ZonePanelProps {
    zones: Zone[];
    selectedZoneId: string | null;
    onSelectZone: (zoneId: string | null) => void;
    onToggleZone: (zoneId: string) => void;
    onDeleteZone: (zoneId: string) => void;
    onUpdateZone: (zone: Zone) => void;
    onStartDrawing: () => void;
    isDrawing: boolean;
}

/**
 * Panel lateral de gestión de zonas
 */
export function ZonePanel({
    zones,
    selectedZoneId,
    onSelectZone,
    onToggleZone,
    onDeleteZone,
    onUpdateZone,
    onStartDrawing,
    isDrawing,
}: ZonePanelProps) {
    const selectedZone = zones.find(z => z.id === selectedZoneId);

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-border">
                <div className="flex items-center justify-between mb-2">
                    <h2 className="text-lg font-semibold">Zonas de Seguridad</h2>
                    <span className="text-xs text-muted-foreground">{zones.length} zonas</span>
                </div>
                <p className="text-sm text-muted-foreground">
                    Define áreas de advertencia y peligro para detectar intrusiones.
                </p>
            </div>

            {/* Zone List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {zones.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                        <svg className="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                        </svg>
                        <p className="text-sm">No hay zonas definidas</p>
                        <p className="text-xs mt-1">Haz clic en "Nueva Zona" para crear una</p>
                    </div>
                ) : (
                    zones.map((zone) => (
                        <div
                            key={zone.id}
                            onClick={() => onSelectZone(zone.id === selectedZoneId ? null : zone.id)}
                            className={`
                                p-3 rounded-lg border cursor-pointer transition-all
                                ${selectedZoneId === zone.id
                                    ? 'border-primary bg-primary/10'
                                    : 'border-border hover:border-primary/50 bg-card'
                                }
                                ${!zone.enabled ? 'opacity-50' : ''}
                            `}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-3 h-3 rounded-full"
                                        style={{ backgroundColor: zone.color }}
                                    />
                                    <span className="font-medium text-sm">{zone.name}</span>
                                </div>
                                <span className={`
                                    text-xs px-2 py-0.5 rounded
                                    ${zone.type === 'danger'
                                        ? 'bg-red-500/20 text-red-500'
                                        : 'bg-yellow-500/20 text-yellow-500'
                                    }
                                `}>
                                    {zone.type === 'danger' ? '🚨 Peligro' : '⚠️ Advertencia'}
                                </span>
                            </div>

                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span>{zone.polygon.length} puntos</span>
                                <span>•</span>
                                <span>{zone.enabled ? 'Activa' : 'Desactivada'}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Selected Zone Editor */}
            {selectedZone && (
                <div className="p-4 border-t border-border bg-card/50">
                    <h3 className="text-sm font-semibold mb-3">Editar Zona</h3>

                    {/* Name */}
                    <label className="block mb-3">
                        <span className="text-xs text-muted-foreground">Nombre</span>
                        <input
                            type="text"
                            value={selectedZone.name}
                            onChange={(e) => onUpdateZone({ ...selectedZone, name: e.target.value })}
                            className="input mt-1 text-sm"
                        />
                    </label>

                    {/* Type */}
                    <label className="block mb-3">
                        <span className="text-xs text-muted-foreground">Tipo</span>
                        <select
                            value={selectedZone.type}
                            onChange={(e) => onUpdateZone({
                                ...selectedZone,
                                type: e.target.value as 'warning' | 'danger',
                                color: e.target.value === 'danger' ? '#ef4444' : '#f59e0b'
                            })}
                            className="input mt-1 text-sm"
                        >
                            <option value="warning">⚠️ Advertencia</option>
                            <option value="danger">🚨 Peligro</option>
                        </select>
                    </label>

                    {/* Color */}
                    <label className="block mb-4">
                        <span className="text-xs text-muted-foreground">Color</span>
                        <div className="flex items-center gap-2 mt-1">
                            <input
                                type="color"
                                value={selectedZone.color}
                                onChange={(e) => onUpdateZone({ ...selectedZone, color: e.target.value })}
                                className="w-10 h-8 rounded border border-border cursor-pointer"
                            />
                            <input
                                type="text"
                                value={selectedZone.color}
                                onChange={(e) => onUpdateZone({ ...selectedZone, color: e.target.value })}
                                className="input flex-1 text-sm font-mono"
                            />
                        </div>
                    </label>

                    {/* Actions */}
                    <div className="flex gap-2">
                        <button
                            onClick={() => onToggleZone(selectedZone.id)}
                            className={`btn flex-1 text-xs ${selectedZone.enabled ? 'btn-secondary' : 'btn-primary'}`}
                        >
                            {selectedZone.enabled ? 'Desactivar' : 'Activar'}
                        </button>
                        <button
                            onClick={() => {
                                onDeleteZone(selectedZone.id);
                                onSelectZone(null);
                            }}
                            className="btn btn-destructive text-xs"
                        >
                            Eliminar
                        </button>
                    </div>
                </div>
            )}

            {/* Footer - Add Zone */}
            <div className="p-4 border-t border-border">
                <button
                    onClick={onStartDrawing}
                    disabled={isDrawing}
                    className="btn btn-primary w-full"
                >
                    {isDrawing ? (
                        <>
                            <span className="w-2 h-2 bg-white rounded-full animate-pulse mr-2" />
                            Dibujando zona...
                        </>
                    ) : (
                        <>
                            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Nueva Zona
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}

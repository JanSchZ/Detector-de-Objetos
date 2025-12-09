'use client';

import { useState, useEffect, useRef } from 'react';
import {
    getRecordings,
    deleteRecording,
    getRecordingVideoUrl,
    Recording,
    RecordingsResponse,
} from '@/lib/api';

interface RecordingsViewerProps {
    onClose?: () => void;
}

export default function RecordingsViewer({ onClose }: RecordingsViewerProps) {
    const [recordings, setRecordings] = useState<Recording[]>([]);
    const [totalSizeMb, setTotalSizeMb] = useState(0);
    const [maxSizeMb, setMaxSizeMb] = useState(5000);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedRecording, setSelectedRecording] = useState<Recording | null>(null);
    const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
    const videoRef = useRef<HTMLVideoElement>(null);

    useEffect(() => {
        loadRecordings();
    }, []);

    const loadRecordings = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getRecordings();
            setRecordings(data.recordings);
            setTotalSizeMb(data.total_size_mb);
            setMaxSizeMb(data.max_size_mb);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error cargando grabaciones');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (recordingId: string) => {
        try {
            await deleteRecording(recordingId);
            setRecordings((prev) => prev.filter((r) => r.id !== recordingId));
            setDeleteConfirm(null);
            if (selectedRecording?.id === recordingId) {
                setSelectedRecording(null);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Error eliminando grabación');
        }
    };

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const formatSize = (bytes: number) => {
        const mb = bytes / (1024 * 1024);
        return mb < 1 ? `${(bytes / 1024).toFixed(1)} KB` : `${mb.toFixed(1)} MB`;
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString('es-CL', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const storagePercent = (totalSizeMb / maxSizeMb) * 100;

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
                <div className="flex items-center gap-3">
                    <span className="text-xl">🎬</span>
                    <h2 className="text-lg font-semibold text-foreground">Grabaciones</h2>
                    <span className="chip">{recordings.length}</span>
                </div>
                {onClose && (
                    <button onClick={onClose} className="btn-ghost p-2 rounded-md">
                        ✕
                    </button>
                )}
            </div>

            {/* Storage Bar */}
            <div className="px-4 py-3 bg-secondary/50 border-b border-border">
                <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Almacenamiento</span>
                    <span className="text-foreground font-medium">
                        {totalSizeMb.toFixed(1)} / {maxSizeMb} MB
                    </span>
                </div>
                <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                    <div
                        className={`h-full transition-all duration-300 ${storagePercent > 90
                                ? 'bg-destructive'
                                : storagePercent > 70
                                    ? 'bg-warning'
                                    : 'bg-primary'
                            }`}
                        style={{ width: `${Math.min(storagePercent, 100)}%` }}
                    />
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 flex overflow-hidden">
                {/* Recordings List */}
                <div className="w-1/2 border-r border-border overflow-y-auto">
                    {loading ? (
                        <div className="flex items-center justify-center h-32">
                            <div className="animate-pulse text-muted-foreground">Cargando...</div>
                        </div>
                    ) : error ? (
                        <div className="p-4 text-destructive text-sm">{error}</div>
                    ) : recordings.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
                            <span className="text-3xl mb-2">📹</span>
                            <span className="text-sm">Sin grabaciones</span>
                        </div>
                    ) : (
                        <div className="divide-y divide-border">
                            {recordings.map((recording) => (
                                <div
                                    key={recording.id}
                                    onClick={() => setSelectedRecording(recording)}
                                    className={`p-3 cursor-pointer transition-colors ${selectedRecording?.id === recording.id
                                            ? 'bg-primary/10 border-l-2 border-primary'
                                            : 'hover:bg-secondary/50'
                                        }`}
                                >
                                    <div className="flex items-start justify-between">
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium text-foreground truncate">
                                                {recording.filename}
                                            </div>
                                            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                                                <span>{formatDate(recording.created_at)}</span>
                                                <span>•</span>
                                                <span>{formatDuration(recording.duration_seconds)}</span>
                                                <span>•</span>
                                                <span>{formatSize(recording.file_size_bytes)}</span>
                                            </div>
                                        </div>
                                        {!recording.exists && (
                                            <span className="chip text-destructive bg-destructive/10">
                                                perdido
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Video Player */}
                <div className="w-1/2 flex flex-col bg-black/20">
                    {selectedRecording ? (
                        <>
                            <div className="flex-1 flex items-center justify-center p-4">
                                {selectedRecording.exists ? (
                                    <video
                                        ref={videoRef}
                                        src={getRecordingVideoUrl(selectedRecording.id)}
                                        controls
                                        className="max-w-full max-h-full rounded-md"
                                    />
                                ) : (
                                    <div className="text-center text-muted-foreground">
                                        <span className="text-4xl mb-2 block">⚠️</span>
                                        <span>Archivo no encontrado</span>
                                    </div>
                                )}
                            </div>
                            {/* Actions */}
                            <div className="p-4 border-t border-border bg-card">
                                <div className="flex items-center justify-between">
                                    <div className="text-sm text-muted-foreground">
                                        {selectedRecording.resolution && (
                                            <span className="chip mr-2">{selectedRecording.resolution}</span>
                                        )}
                                    </div>
                                    {deleteConfirm === selectedRecording.id ? (
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-muted-foreground">¿Eliminar?</span>
                                            <button
                                                onClick={() => handleDelete(selectedRecording.id)}
                                                className="btn-destructive text-xs py-1 px-2"
                                            >
                                                Sí
                                            </button>
                                            <button
                                                onClick={() => setDeleteConfirm(null)}
                                                className="btn-secondary text-xs py-1 px-2"
                                            >
                                                No
                                            </button>
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => setDeleteConfirm(selectedRecording.id)}
                                            className="btn-ghost text-destructive text-xs py-1.5 px-3"
                                        >
                                            🗑 Eliminar
                                        </button>
                                    )}
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-muted-foreground">
                            <div className="text-center">
                                <span className="text-3xl mb-2 block">👈</span>
                                <span className="text-sm">Selecciona una grabación</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

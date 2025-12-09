'use client';

interface VideoCanvasProps {
    frame: string | null;
    frameSize: { width: number; height: number } | null;
    isConnected: boolean;
    statusMessage?: string | null;
    hasNoCameras?: boolean;
    onOpenSettings?: () => void;
}

/**
 * Full-screen video display component with setup instructions
 */
export function VideoCanvas({
    frame,
    frameSize,
    isConnected,
    statusMessage,
    hasNoCameras = false,
    onOpenSettings
}: VideoCanvasProps) {
    // Show setup instructions when no cameras are available
    if (hasNoCameras) {
        return (
            <div className="w-full h-full bg-black flex items-center justify-center">
                <div className="text-center max-w-md mx-auto p-6">
                    <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-primary/10 flex items-center justify-center">
                        <svg className="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <h2 className="text-lg font-semibold text-white mb-2">No se detectaron cámaras</h2>
                    <p className="text-sm text-muted-foreground mb-6">
                        Conecta una webcam o configura una cámara IP para comenzar la detección.
                    </p>

                    <div className="space-y-4 text-left">
                        <div className="p-4 rounded-lg bg-card/50 border border-border">
                            <h3 className="text-sm font-medium text-white mb-2">📷 Webcam</h3>
                            <p className="text-xs text-muted-foreground">
                                Conecta una webcam USB y recarga la página. En macOS, se te pedirá permiso para acceder a la cámara.
                            </p>
                        </div>

                        <div className="p-4 rounded-lg bg-card/50 border border-border">
                            <h3 className="text-sm font-medium text-white mb-2">📱 Cámara IP (Celular)</h3>
                            <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
                                <li>Descarga IP Webcam o DroidCam en tu celular</li>
                                <li>Inicia el servidor en la app</li>
                                <li>Copia la URL del stream (ej: http://192.168.1.100:8080/videofeed)</li>
                            </ol>
                            {onOpenSettings && (
                                <button
                                    onClick={onOpenSettings}
                                    className="mt-3 text-xs text-primary hover:text-primary/80 underline"
                                >
                                    Configurar cámara IP →
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-full bg-black flex items-center justify-center">
            {frame && isConnected ? (
                <img
                    src={frame}
                    alt="Detection stream"
                    className="max-w-full max-h-full object-contain"
                />
            ) : (
                <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground">
                    <svg
                        className="w-16 h-16 opacity-30"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1}
                            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                    </svg>
                    <p className="text-sm text-center max-w-xs">
                        {statusMessage || (isConnected ? 'Esperando video...' : 'Conectando con el servidor...')}
                    </p>
                    {isConnected && !frame && (
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
                            <span className="text-xs text-yellow-500">Iniciando cámara...</span>
                        </div>
                    )}
                </div>
            )}

            {/* Live indicator */}
            {isConnected && frame && (
                <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 rounded bg-card/80 backdrop-blur-sm border border-border">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                    </span>
                    <span className="text-xs font-medium">EN VIVO</span>
                </div>
            )}
        </div>
    );
}


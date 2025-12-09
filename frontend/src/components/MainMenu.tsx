'use client';

import { useState, useEffect } from 'react';
import { getAvailableClasses, getAvailableModels } from '@/lib/api';

interface MainMenuProps {
    videoSource: 'webcam' | 'ip_camera';
    onVideoSourceChange: (source: 'webcam' | 'ip_camera') => void;
    webcamIndex: number;
    onWebcamIndexChange: (index: number) => void;
    ipCameraUrl: string;
    onIpCameraUrlChange: (url: string) => void;
    modelSize: string;
    onModelSizeChange: (size: string) => void;
    poseEnabled: boolean;
    onPoseEnabledChange: (enabled: boolean) => void;
    poseModelSize: string;
    onPoseModelSizeChange: (size: string) => void;
    enabledClasses: number[];
    onEnabledClassesChange: (classes: number[]) => void;
    onTestCamera: () => void;
    cameraStatus: string | null;
    isTestingCamera: boolean;
}

interface ClassInfo {
    id: number;
    name: string;
}

interface ModelInfo {
    id: string;
    name: string;
    file: string;
    description: string;
}

interface PoseModelInfo {
    id: string;
    name: string;
    description: string;
}

/**
 * Main menu panel for source, model, and class selection
 */
export function MainMenu({
    videoSource,
    onVideoSourceChange,
    webcamIndex,
    onWebcamIndexChange,
    ipCameraUrl,
    onIpCameraUrlChange,
    modelSize,
    onModelSizeChange,
    poseEnabled,
    onPoseEnabledChange,
    poseModelSize,
    onPoseModelSizeChange,
    enabledClasses,
    onEnabledClassesChange,
    onTestCamera,
    cameraStatus,
    isTestingCamera,
}: MainMenuProps) {
    const [classes, setClasses] = useState<ClassInfo[]>([]);
    const [models, setModels] = useState<ModelInfo[]>([]);
    const [poseModels, setPoseModels] = useState<PoseModelInfo[]>([]);
    const [classSearch, setClassSearch] = useState('');
    const [localIpUrl, setLocalIpUrl] = useState(ipCameraUrl);

    useEffect(() => {
        // Fetch available classes and models
        getAvailableClasses().then((data) => setClasses(data.classes));
        getAvailableModels().then((data) => {
            setModels(data.models);
            if (data.pose_models) {
                setPoseModels(data.pose_models);
            }
        });
    }, []);

    useEffect(() => {
        setLocalIpUrl(ipCameraUrl);
    }, [ipCameraUrl]);

    const filteredClasses = classes.filter((c) =>
        c.name.toLowerCase().includes(classSearch.toLowerCase())
    );

    const handleClassToggle = (classId: number) => {
        if (enabledClasses.includes(classId)) {
            onEnabledClassesChange(enabledClasses.filter((id) => id !== classId));
        } else {
            onEnabledClassesChange([...enabledClasses, classId]);
        }
    };

    const handleSelectAll = () => {
        onEnabledClassesChange(classes.map((c) => c.id));
    };

    const handleSelectNone = () => {
        onEnabledClassesChange([]);
    };

    const handleIpUrlBlur = () => {
        if (localIpUrl !== ipCameraUrl) {
            onIpCameraUrlChange(localIpUrl);
        }
    };

    return (
        <div className="space-y-5">
            {/* Video Source */}
            <section>
                <h3 className="label mb-2">Fuente de Video</h3>
                <div className="space-y-2">
                    <div className="flex gap-2">
                        <button
                            onClick={() => onVideoSourceChange('webcam')}
                            className={`flex-1 py-2 px-3 text-xs font-medium rounded border transition-colors ${videoSource === 'webcam'
                                ? 'bg-primary/15 text-primary border-primary/30'
                                : 'bg-secondary text-muted-foreground border-border hover:bg-muted'
                                }`}
                        >
                            <svg className="w-4 h-4 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                            Webcam
                        </button>
                        <button
                            onClick={() => onVideoSourceChange('ip_camera')}
                            className={`flex-1 py-2 px-3 text-xs font-medium rounded border transition-colors ${videoSource === 'ip_camera'
                                ? 'bg-primary/15 text-primary border-primary/30'
                                : 'bg-secondary text-muted-foreground border-border hover:bg-muted'
                                }`}
                        >
                            <svg className="w-4 h-4 mx-auto mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                            </svg>
                            IP/Móvil
                        </button>
                    </div>

                    {videoSource === 'webcam' ? (
                        <div>
                            <label className="text-xs text-muted-foreground">Índice</label>
                            <input
                                type="number"
                                min={0}
                                max={10}
                                value={webcamIndex}
                                onChange={(e) => onWebcamIndexChange(parseInt(e.target.value) || 0)}
                                className="input mt-1"
                            />
                        </div>
                    ) : (
                        <div className="space-y-2">
                            <div>
                                <label className="text-xs text-muted-foreground">URL del stream</label>
                                <input
                                    type="text"
                                    value={localIpUrl}
                                    onChange={(e) => setLocalIpUrl(e.target.value)}
                                    onBlur={handleIpUrlBlur}
                                    onKeyDown={(e) => e.key === 'Enter' && handleIpUrlBlur()}
                                    placeholder="http://192.168.1.100:8080/video"
                                    className="input mt-1"
                                />
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={onTestCamera}
                                    disabled={isTestingCamera}
                                    className="btn btn-secondary text-xs py-1.5"
                                >
                                    {isTestingCamera ? 'Probando...' : 'Probar conexión'}
                                </button>
                                {cameraStatus && (
                                    <span className="text-xs text-muted-foreground">{cameraStatus}</span>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </section>

            {/* Model Selection */}
            <section>
                <h3 className="label mb-2">Modelo YOLO</h3>
                <div className="grid grid-cols-2 gap-1.5">
                    {models.map((model) => {
                        // Compare with both alias (nano) and full value (yolo11n.pt)
                        const isSelected = modelSize === model.id || modelSize === model.file;
                        return (
                            <button
                                key={model.id}
                                onClick={() => onModelSizeChange(model.id)}
                                className={`py-2 px-2 text-xs rounded border transition-colors text-left ${isSelected
                                    ? 'bg-primary/15 text-primary border-primary/30'
                                    : 'bg-secondary text-muted-foreground border-border hover:bg-muted'
                                    }`}
                            >
                                <div className="font-medium">{model.id.charAt(0).toUpperCase() + model.id.slice(1)}</div>
                                <div className="text-[10px] opacity-70">{model.description}</div>
                            </button>
                        );
                    })}
                </div>
            </section>

            {/* Pose Estimation */}
            <section>
                <div className="flex items-center justify-between mb-2">
                    <h3 className="label">Pose Estimation</h3>
                    <label className="relative inline-flex items-center cursor-pointer">
                        <input
                            type="checkbox"
                            checked={poseEnabled}
                            onChange={(e) => onPoseEnabledChange(e.target.checked)}
                            className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-secondary rounded-full peer peer-checked:bg-primary/30 transition-colors" />
                        <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-muted-foreground rounded-full peer-checked:translate-x-4 peer-checked:bg-primary transition-all" />
                    </label>
                </div>
                {poseEnabled && poseModels.length > 0 && (
                    <div className="grid grid-cols-2 gap-1.5">
                        {poseModels.map((model) => (
                            <button
                                key={model.id}
                                onClick={() => onPoseModelSizeChange(model.id)}
                                className={`py-2 px-2 text-xs rounded border transition-colors text-left ${poseModelSize === model.id
                                    ? 'bg-primary/15 text-primary border-primary/30'
                                    : 'bg-secondary text-muted-foreground border-border hover:bg-muted'
                                    }`}
                            >
                                <div className="font-medium">{model.name}</div>
                                <div className="text-[10px] opacity-70">{model.description}</div>
                            </button>
                        ))}
                    </div>
                )}
            </section>

            {/* Class Selection */}
            <section>
                <div className="flex items-center justify-between mb-2">
                    <h3 className="label">Clases a Detectar</h3>
                    <span className="text-xs text-muted-foreground">{enabledClasses.length}/{classes.length}</span>
                </div>

                <input
                    type="text"
                    value={classSearch}
                    onChange={(e) => setClassSearch(e.target.value)}
                    placeholder="Buscar clase..."
                    className="input mb-2"
                />

                <div className="flex gap-2 mb-2">
                    <button onClick={handleSelectAll} className="btn btn-secondary text-xs py-1 flex-1">
                        Todas
                    </button>
                    <button onClick={handleSelectNone} className="btn btn-secondary text-xs py-1 flex-1">
                        Ninguna
                    </button>
                </div>

                <div className="max-h-48 overflow-y-auto space-y-0.5 border border-border rounded p-2 bg-secondary/30">
                    {filteredClasses.map((cls) => (
                        <label
                            key={cls.id}
                            className="flex items-center gap-2 py-1 px-1 rounded hover:bg-secondary cursor-pointer"
                        >
                            <input
                                type="checkbox"
                                checked={enabledClasses.includes(cls.id)}
                                onChange={() => handleClassToggle(cls.id)}
                                className="w-3.5 h-3.5 rounded border-border bg-secondary text-primary"
                            />
                            <span className="text-xs capitalize">{cls.name}</span>
                        </label>
                    ))}
                </div>
            </section>
        </div>
    );
}

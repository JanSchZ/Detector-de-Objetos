'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { useDetections } from '@/hooks/useDetections';
import {
  VideoCanvas,
  ZoneEditor,
  ZonePanel,
  AlertBanner,
  AlertList,
  Drawer,
  TopBar,
  OverlayToggles,
  QuickStats,
  MainMenu,
  SettingsPanel,
  AnalyticsPanel,
  AIAssistant,
  Zone,
} from '@/components';
import {
  checkHealth,
  getConfig,
  DetectionConfig,
  createZone,
  deleteZone,
  updateZone,
  toggleZone,
  updateConfig,
  checkCamera,
  CameraStatus,
  getAvailableCameras,
  CamerasResponse,
} from '@/lib/api';

type DrawerType = 'menu' | 'settings' | 'analytics' | 'zones' | 'alerts' | null;

export default function Home() {
  // Backend & connection state
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [config, setConfig] = useState<DetectionConfig | null>(null);

  // Drawers
  const [activeDrawer, setActiveDrawer] = useState<DrawerType>(null);

  // Fullscreen
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Session tracking
  const [sessionStart, setSessionStart] = useState<number | null>(null);

  // Camera test
  const [cameraStatus, setCameraStatus] = useState<string | null>(null);
  const [isTestingCamera, setIsTestingCamera] = useState(false);

  // Available cameras
  const [camerasInfo, setCamerasInfo] = useState<CamerasResponse | null>(null);
  const hasNoCameras = camerasInfo !== null && camerasInfo.total === 0 && !camerasInfo.has_ip_camera_configured;

  // Zone selection
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [isDrawingZone, setIsDrawingZone] = useState(false);

  // Overlay toggles
  const [overlays, setOverlays] = useState({
    boxes: true,
    labels: true,
    confidence: true,
    trackerIds: false,
    zones: true,
    trails: false,
  });

  const {
    status,
    trackingData,
    frame,
    frameSize,
    streamStatus,
    zones,
    alerts,
    error,
    fps,
    sendCommand,
  } = useDetections({ includeFrames: true });

  const isConnected = status === 'connected';

  // Check backend health and fetch cameras
  useEffect(() => {
    const checkBackend = async () => {
      const isHealthy = await checkHealth();
      setBackendStatus(isHealthy ? 'online' : 'offline');
      if (isHealthy) {
        try {
          const [cfg, cameras] = await Promise.all([
            getConfig(),
            getAvailableCameras(),
          ]);
          setConfig(cfg);
          setCamerasInfo(cameras);
        } catch (err) {
          console.error('Failed to fetch config/cameras:', err);
        }
      }
    };

    checkBackend();
    const interval = setInterval(() => {
      if (backendStatus === 'offline') checkBackend();
    }, 5000);

    return () => clearInterval(interval);
  }, [backendStatus]);

  // Auto-connect when backend is online (useDetections now has autoConnect=true)
  // The hook handles this automatically

  // Track session start
  useEffect(() => {
    if (isConnected && !sessionStart) {
      setSessionStart(Date.now());
    } else if (!isConnected) {
      setSessionStart(null);
    }
  }, [isConnected, sessionStart]);

  // Fullscreen handlers
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Screenshot handler
  const handleScreenshot = useCallback(() => {
    if (!frame) return;
    const a = document.createElement('a');
    a.href = frame;
    a.download = `argos-capture-${Date.now()}.jpg`;
    a.click();
  }, [frame]);

  // Config update handlers
  const handleConfigUpdate = async (updates: Partial<DetectionConfig>) => {
    try {
      const newConfig = await updateConfig(updates);
      setConfig(newConfig);
    } catch (err) {
      console.error('Failed to update config:', err);
    }
  };

  // Camera test
  const handleTestCamera = async () => {
    setIsTestingCamera(true);
    setCameraStatus(null);
    try {
      const status: CameraStatus = await checkCamera();
      const res = status.resolution;
      setCameraStatus(`OK: ${res.width}x${res.height}`);
    } catch (err) {
      setCameraStatus(err instanceof Error ? err.message : 'Error');
    } finally {
      setIsTestingCamera(false);
    }
  };

  // Zone handlers
  const handleZoneCreate = async (zone: Zone) => {
    try {
      await createZone(zone);
      sendCommand({ command: 'add_zone', zone });
      setIsDrawingZone(false);
    } catch (err) {
      console.error('Failed to create zone:', err);
    }
  };

  const handleZoneDelete = async (zoneId: string) => {
    try {
      await deleteZone(zoneId);
      sendCommand({ command: 'remove_zone', zone_id: zoneId });
      if (selectedZoneId === zoneId) {
        setSelectedZoneId(null);
      }
    } catch (err) {
      console.error('Failed to delete zone:', err);
    }
  };

  const handleZoneUpdate = async (zone: Zone) => {
    try {
      await updateZone(zone);
      sendCommand({ command: 'update_zone', zone });
    } catch (err) {
      console.error('Failed to update zone:', err);
    }
  };

  const handleZoneToggle = async (zoneId: string) => {
    try {
      await toggleZone(zoneId);
      sendCommand({ command: 'toggle_zone', zone_id: zoneId });
    } catch (err) {
      console.error('Failed to toggle zone:', err);
    }
  };

  // Overlay toggle handler
  const handleOverlayToggle = (id: string) => {
    setOverlays((prev) => ({ ...prev, [id]: !prev[id as keyof typeof prev] }));
    // TODO: Send overlay config to backend when supported
  };

  // Zone alerts count
  const zoneAlerts = { warning: 0, danger: 0 };
  // Could compute from actual zone events if available

  // Quick overlay toggle options
  const overlayOptions = [
    { id: 'boxes', label: 'Boxes', enabled: overlays.boxes },
    { id: 'labels', label: 'Etiquetas', enabled: overlays.labels },
    { id: 'trackerIds', label: 'IDs', enabled: overlays.trackerIds },
    { id: 'zones', label: 'Zonas', enabled: overlays.zones },
  ];

  return (
    <div ref={containerRef} className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Alert Banner */}
      <AlertBanner alerts={alerts} />

      {/* Top Bar */}
      <TopBar
        onMenuClick={() => setActiveDrawer('menu')}
        onSettingsClick={() => setActiveDrawer('settings')}
        onFullscreenToggle={toggleFullscreen}
        onScreenshot={handleScreenshot}
        isConnected={isConnected}
        isFullscreen={isFullscreen}
        backendStatus={backendStatus}
        fps={fps}
        inferenceTime={trackingData?.inference_time_ms ?? 0}
        camerasInfo={camerasInfo}
        onCameraChange={async (index) => {
          await handleConfigUpdate({ webcam_index: index });
          // Refetch cameras to update current state
          const cameras = await getAvailableCameras();
          setCamerasInfo(cameras);
        }}
        onSourceChange={async (source) => {
          await handleConfigUpdate({ video_source: source });
          const cameras = await getAvailableCameras();
          setCamerasInfo(cameras);
        }}
      />

      {/* Main Video Area */}
      <main className="flex-1 relative overflow-hidden">
        {error && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 px-4 py-2 rounded bg-destructive/90 text-sm text-white">
            {error}
          </div>
        )}

        {/* Video Canvas - Full Area */}
        <div className="absolute inset-0">
          <VideoCanvas
            frame={frame}
            frameSize={frameSize}
            isConnected={isConnected}
            statusMessage={streamStatus}
            hasNoCameras={hasNoCameras}
            onOpenSettings={() => setActiveDrawer('menu')}
          />

          {/* Zone Editor Overlay */}
          {overlays.zones && (
            <ZoneEditor
              zones={zones}
              frameSize={frameSize}
              onZoneCreate={handleZoneCreate}
              onZoneDelete={handleZoneDelete}
              onZoneUpdate={handleZoneUpdate}
              isEditing={isDrawingZone}
              onEditingChange={setIsDrawingZone}
              selectedZoneId={selectedZoneId}
              onSelectZone={setSelectedZoneId}
            />
          )}
        </div>

        {/* Floating Controls - Bottom Left */}
        <div className="absolute bottom-4 left-4 z-10">
          <OverlayToggles options={overlayOptions} onToggle={handleOverlayToggle} />
        </div>

        {/* Floating Stats - Bottom Right */}
        <div className="absolute bottom-4 right-4 z-10 w-64">
          <QuickStats
            counts={trackingData?.counts ?? {}}
            zoneAlerts={zoneAlerts}
            isConnected={isConnected}
          />
        </div>

        {/* Additional action buttons */}
        <div className="absolute top-4 right-4 z-10 flex gap-2">
          <button
            onClick={() => setActiveDrawer('analytics')}
            className="p-2 rounded bg-card/80 backdrop-blur-sm border border-border hover:bg-secondary transition-colors"
            title="Analytics"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </button>
          <button
            onClick={() => setActiveDrawer('alerts')}
            className="p-2 rounded bg-card/80 backdrop-blur-sm border border-border hover:bg-secondary transition-colors"
            title="Alertas"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </button>
          <button
            onClick={() => setActiveDrawer('zones')}
            className="p-2 rounded bg-card/80 backdrop-blur-sm border border-border hover:bg-secondary transition-colors"
            title="Zonas"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
            </svg>
          </button>
        </div>
      </main>

      {/* Drawers */}
      <Drawer
        isOpen={activeDrawer === 'menu'}
        onClose={() => setActiveDrawer(null)}
        title="Configuración Principal"
        side="left"
      >
        {config && (
          <MainMenu
            videoSource={config.video_source}
            onVideoSourceChange={(source) => handleConfigUpdate({ video_source: source })}
            webcamIndex={config.webcam_index}
            onWebcamIndexChange={(index) => handleConfigUpdate({ webcam_index: index })}
            ipCameraUrl={config.ip_camera_url}
            onIpCameraUrlChange={(url) => handleConfigUpdate({ ip_camera_url: url })}
            modelSize={config.model_size}
            onModelSizeChange={(size) => handleConfigUpdate({ model_size: size })}
            poseEnabled={config.pose_enabled ?? false}
            onPoseEnabledChange={(enabled) => handleConfigUpdate({ pose_enabled: enabled })}
            poseModelSize={config.pose_model_size ?? 'yolo11n-pose.pt'}
            onPoseModelSizeChange={(size) => handleConfigUpdate({ pose_model_size: size })}
            enabledClasses={config.enabled_classes}
            onEnabledClassesChange={(classes) => handleConfigUpdate({ enabled_classes: classes })}
            onTestCamera={handleTestCamera}
            cameraStatus={cameraStatus}
            isTestingCamera={isTestingCamera}
          />
        )}
      </Drawer>

      <Drawer
        isOpen={activeDrawer === 'settings'}
        onClose={() => setActiveDrawer(null)}
        title="Ajustes"
        side="right"
      >
        {config && (
          <SettingsPanel
            confidenceThreshold={config.confidence_threshold}
            onConfidenceChange={(v) => handleConfigUpdate({ confidence_threshold: v })}
            iouThreshold={config.iou_threshold}
            onIouChange={(v) => handleConfigUpdate({ iou_threshold: v })}
            maxFps={config.max_fps}
            onMaxFpsChange={(v) => handleConfigUpdate({ max_fps: v })}
            overlays={overlays}
            onOverlayChange={(key, value) => setOverlays((prev) => ({ ...prev, [key]: value }))}
            boxColor={config.box_color}
            onBoxColorChange={(color) => handleConfigUpdate({ box_color: color })}
          />
        )}
      </Drawer>

      <Drawer
        isOpen={activeDrawer === 'analytics'}
        onClose={() => setActiveDrawer(null)}
        title="Analytics"
        side="right"
      >
        <AnalyticsPanel
          objects={trackingData?.objects ?? []}
          counts={trackingData?.counts ?? {}}
          sessionStart={sessionStart}
          isConnected={isConnected}
        />
      </Drawer>

      <Drawer
        isOpen={activeDrawer === 'alerts'}
        onClose={() => setActiveDrawer(null)}
        title="Alertas"
        side="right"
      >
        <div className="space-y-4">
          <h3 className="label">Historial de Alertas</h3>
          <AlertList alerts={alerts} />
        </div>
      </Drawer>

      <Drawer
        isOpen={activeDrawer === 'zones'}
        onClose={() => setActiveDrawer(null)}
        title="Zonas de Seguridad"
        side="right"
      >
        <ZonePanel
          zones={zones}
          selectedZoneId={selectedZoneId}
          onSelectZone={setSelectedZoneId}
          onToggleZone={handleZoneToggle}
          onDeleteZone={handleZoneDelete}
          onUpdateZone={handleZoneUpdate}
          onStartDrawing={() => setIsDrawingZone(true)}
          isDrawing={isDrawingZone}
        />
      </Drawer>

      {/* Offline Overlay */}
      {backendStatus === 'offline' && (
        <div className="fixed inset-0 bg-background/95 flex items-center justify-center z-50">
          <div className="text-center max-w-sm mx-4">
            <div className="w-12 h-12 mx-auto mb-4 rounded bg-destructive/15 flex items-center justify-center">
              <svg className="w-6 h-6 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold mb-2">Backend Offline</h2>
            <p className="text-sm text-muted-foreground mb-4">Inicia el servidor:</p>
            <code className="block text-xs font-mono bg-secondary p-3 rounded border border-border text-muted-foreground">
              cd backend && uvicorn app.main:app --reload
            </code>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <AIAssistant
        currentFrame={frame}
        onConfigChange={async () => {
          const cfg = await getConfig();
          setConfig(cfg);
        }}
        onZoneChange={() => {
          // Trigger a refresh of zones by forcing a re-render or re-fetch
          // In this architecture, zones are managed by useDetections hook
          // Ideally we should have a way to refresh them
          sendCommand({ command: 'get_zones' });
        }}
      />
    </div>
  );
}

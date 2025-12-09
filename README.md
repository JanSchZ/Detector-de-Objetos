# Argos 👁️

> *El gigante de los 100 ojos* - Sistema de detección de objetos multi-backend con IA

Sistema de vigilancia con IA para detección de objetos, tracking persistente, zonas de seguridad y alertas push.

## 🚀 Quick Start

### Backend (Python)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0
```

### Frontend (Next.js)
```bash
cd frontend
npm install && npm run dev
```

### Mobile (Expo)
```bash
cd mobile
npm install
npx expo start
```

### Variables de entorno útiles

- `VM_VIDEO_SOURCE` (`webcam` | `ip_camera`)
- `VM_IP_CAMERA_URL` (ej: `http://192.168.1.100:8080/videofeed`)
- `VM_WEBCAM_INDEX` (índice numérico)
- `VM_MODEL_SIZE` (`nano`, `small`, `medium`, `large`, `xlarge` o nombre del `.pt`)

## 📱 Configurar App Móvil

1. Edita `mobile/src/lib/api.ts`
2. Cambia `baseUrl` a la IP de tu PC:
   ```typescript
   baseUrl: 'http://192.168.1.XXX:8000'
   ```
3. Escanea QR con Expo Go

## 🎯 Features

| Feature | Backend | Web | Mobile |
|---------|---------|-----|--------|
| Detección YOLOv11 | ✅ | - | - |
| Tracking ByteTrack | ✅ | ✅ Visualización | ✅ Visualización |
| Zonas de seguridad | ✅ | ✅ Editor | ✅ Vista |
| Alertas push | ✅ Ntfy | ✅ Banner | ✅ Historial |
| Cámara IP | ✅ | Configuración | ✅ Streaming |

## 📁 Estructura

```
VisionMind/
├── backend/          # FastAPI + YOLOv11 + ByteTrack
│   └── app/
│       ├── detection/  # YOLO + Tracker
│       ├── zones/      # Geometría polígonos
│       ├── alerts/     # Push notifications
│       └── api/        # REST + WebSocket
│
├── frontend/         # Next.js + TypeScript
│   └── src/
│       ├── components/  # VideoCanvas, ZoneEditor, Alerts
│       └── hooks/       # useDetections
│
└── mobile/           # Expo + React Native
    └── src/
        ├── screens/   # Camera, Monitor
        └── hooks/     # useDetectionStream
```

## 🔧 API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/camera/status` | GET | Prueba rápida de la fuente de video configurada |
| `/api/config` | GET/PUT | Configuración |
| `/api/zones` | GET/POST/DELETE | CRUD zonas |
| `/api/alerts/config` | GET/PUT | Config alertas |
| `/api/alerts/history` | GET | Historial |
| `/api/alerts/test` | POST | Enviar test |
| `/ws/detect` | WS | Stream detecciones |

## 💻 Hardware

- **PC RTX 3080**: 60+ FPS (CUDA)
- **Mac M4**: 30+ FPS (MPS)

## 📄 License

MIT

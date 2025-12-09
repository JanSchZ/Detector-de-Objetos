#!/bin/bash

# =============================================================================
# VisionMind - Script de inicio rápido para macOS
# Doble click para iniciar backend, frontend y mobile en terminales separadas
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
MOBILE_DIR="$SCRIPT_DIR/mobile"
VENV_ACTIVATE="$BACKEND_DIR/venv/bin/activate"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# =============================================================================
# Helpers
# =============================================================================
err() {
    echo "❌ Error: $1" >&2
    exit 1
}

warn() {
    echo "⚠️  Advertencia: $1" >&2
}

info() {
    echo "ℹ️  $1"
}

# Safely quote strings for shell within AppleScript
sh_quote() {
    local s="$1"
    printf "'%s'" "$(printf %s "$s" | sed "s/'/'\"'\"'/g")"
}

# =============================================================================
# Validaciones
# =============================================================================
command -v osascript >/dev/null 2>&1 || err "Este script requiere 'osascript' (disponible en macOS)."
command -v python3 >/dev/null 2>&1 || err "Python 3 no está instalado."
command -v node >/dev/null 2>&1 || err "Node.js no está instalado."

[ -d "$BACKEND_DIR" ] || err "Directorio backend no encontrado en '$BACKEND_DIR'."
[ -d "$FRONTEND_DIR" ] || err "Directorio frontend no encontrado en '$FRONTEND_DIR'."

# =============================================================================
# Setup automático si es necesario
# =============================================================================

# Backend: crear venv si no existe
if [ ! -f "$VENV_ACTIVATE" ]; then
    info "Creando entorno virtual Python..."
    python3 -m venv "$BACKEND_DIR/venv" || err "No se pudo crear el entorno virtual"
fi

# Backend: siempre sincronizar dependencias (detecta cambios en requirements.txt)
info "Verificando dependencias del backend..."
source "$BACKEND_DIR/venv/bin/activate"

# Instalar/actualizar dependencias
pip install --quiet --upgrade pip
pip install --quiet -r "$BACKEND_DIR/requirements.txt"

# Verificar que google-generativeai está instalado (requerido para el asistente IA)
if ! python3 -c "import google.generativeai" 2>/dev/null; then
    warn "Instalando google-generativeai para el asistente IA..."
    pip install --quiet google-generativeai
fi

deactivate

# Frontend: instalar deps si no existen o package.json cambió
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "Instalando dependencias frontend..."
    cd "$FRONTEND_DIR" && npm install
elif [ "$FRONTEND_DIR/package.json" -nt "$FRONTEND_DIR/node_modules/.package-lock.json" ] 2>/dev/null; then
    info "Actualizando dependencias frontend..."
    cd "$FRONTEND_DIR" && npm install
fi

# =============================================================================
# Solicitar permisos de cámara (macOS)
# =============================================================================
info "Verificando permisos de cámara..."

# Crear script temporal para solicitar permiso de cámara
CAMERA_CHECK_SCRIPT=$(mktemp)
cat > "$CAMERA_CHECK_SCRIPT" << 'PYEOF'
import sys
try:
    import cv2
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            print("✅ Cámara accesible")
            sys.exit(0)
    print("⚠️  No se pudo acceder a la cámara")
    print("   Puede ser que no hay cámara conectada o falta permiso.")
    print("   Ve a: Ajustes del Sistema → Privacidad y seguridad → Cámara")
    print("   y habilita Terminal o tu aplicación de terminal.")
    sys.exit(1)
except Exception as e:
    print(f"⚠️  Error verificando cámara: {e}")
    sys.exit(1)
PYEOF

# Ejecutar con el venv del backend que tiene opencv
source "$VENV_ACTIVATE"
python3 "$CAMERA_CHECK_SCRIPT" 2>/dev/null || true
deactivate
rm -f "$CAMERA_CHECK_SCRIPT"

echo ""

# Mobile: instalar deps si no existen (opcional)
if [ -d "$MOBILE_DIR" ] && [ ! -d "$MOBILE_DIR/node_modules" ]; then
    info "Instalando dependencias mobile..."
    cd "$MOBILE_DIR" && npm install
fi

# =============================================================================
# Construir comandos
# =============================================================================
BACKEND_CMD="cd $(sh_quote "$BACKEND_DIR") && source venv/bin/activate && echo '🚀 Backend iniciando en http://0.0.0.0:$BACKEND_PORT' && uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT"

FRONTEND_CMD="cd $(sh_quote "$FRONTEND_DIR") && echo '🌐 Frontend iniciando en http://localhost:$FRONTEND_PORT' && npm run dev -- --port $FRONTEND_PORT"

MOBILE_CMD=""
if [ -d "$MOBILE_DIR" ]; then
    MOBILE_CMD="cd $(sh_quote "$MOBILE_DIR") && echo '📱 Mobile iniciando...' && npx expo start"
fi

# =============================================================================
# Lanzar terminales
# =============================================================================
info "Iniciando VisionMind..."

osascript <<EOF_APPLESCRIPT
tell application "Terminal"
    activate
    do script "$BACKEND_CMD"
    delay 2
    do script "$FRONTEND_CMD"
end tell
EOF_APPLESCRIPT

# Mobile en terminal separada (opcional)
if [ -n "$MOBILE_CMD" ]; then
    sleep 1
    osascript <<EOF_APPLESCRIPT
tell application "Terminal"
    activate
    do script "$MOBILE_CMD"
end tell
EOF_APPLESCRIPT
fi

# =============================================================================
# Resumen
# =============================================================================
echo ""
echo "=============================================="
echo "  🎯 VisionMind iniciado exitosamente"
echo "=============================================="
echo ""
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  Swagger:  http://localhost:$BACKEND_PORT/docs"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
if [ -d "$MOBILE_DIR" ]; then
    echo "  Mobile:   Escanea QR con Expo Go"
fi
echo ""
echo "  Para detener: cierra las ventanas de Terminal"
echo "  o ejecuta: killall python node 2>/dev/null"
echo ""
echo "=============================================="

# Abrir frontend en navegador
sleep 3
open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true

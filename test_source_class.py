import time
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.video.sources import IPCameraSource

URL = "http://192.168.3.248:8080/videofeed"

print(f"Probando IPCameraSource con: {URL}")
source = IPCameraSource(URL)

print("Iniciando source...")
success = source.start()

if not success:
    # Ahora start() retorna True incluso si falla la conexión inicial (background retry)
    # Pero para este test queremos ver si conecta rápido
    print("⚠️ Start retornó False o hubo warning (esperado si está reconectando)")

# Esperar unos segundos para que conecte
print("Esperando conexión...")
for i in range(10):
    if source.is_opened():
        print("✅ Source reporta is_opened() = True")
        break
    time.sleep(1)
    print(f"Wait {i+1}/10...")

# Intentar leer frames
print("Leyendo frames...")
frames_read = 0
for i in range(20):
    ret, frame = source.read()
    if ret and frame is not None:
        print(f"✅ Frame {i}: {frame.shape}")
        frames_read += 1
    else:
        print(f"❌ Frame {i}: Fallo lectura")
    time.sleep(0.1)

source.stop()

if frames_read > 0:
    print(f"✅ ÉXITO: Se leyeron {frames_read} frames.")
    sys.exit(0)
else:
    print("❌ FALLO: No se leyeron frames.")
    sys.exit(1)

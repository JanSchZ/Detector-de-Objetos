import cv2
import time

URL = "http://192.168.3.248:8080/videofeed"

print(f"Intentando conectar a {URL}...")
cap = cv2.VideoCapture(URL)

if not cap.isOpened():
    print("❌ ERROR: No se pudo abrir el stream con OpenCV.")
else:
    print("✅ Stream abierto correctamente!")
    ret, frame = cap.read()
    if ret:
        print(f"✅ Frame leído: {frame.shape}")
        print("¡FUNCIONA!")
    else:
        print("❌ Stream abierto pero no pude leer frames.")
    cap.release()

"""
AI Assistant powered by Gemini 2.0 Flash.
Helps users understand and configure the Argos detection system.
"""
import os
import asyncio
from pathlib import Path
from typing import List, Optional

# Load .env file if it exists
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.generativeai as genai

# Import tools
from app.api import assistant_tools

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# Enhanced System Prompt for Argos Operator
SYSTEM_PROMPT = """Eres Argos, el operador experto del sistema de vigilancia "El gigante de los 100 ojos".
Tu misión es proteger y asistir al usuario controlando el sistema de visión artificial integral.

## Tu Personalidad:
- Eres profesional, vigilante y eficiente.
- Hablas en español conciso y directo.
- Te refieres al sistema como "Argos" o "nosotros".

## Tus Capacidades (Herramientas):
TIENES CONTROL TOTAL SOBRE EL SISTEMA. ÚSALO.
No le expliques al usuario cómo hacerlo, HAZLO TÚ.

1.  **👁️ Modos de Visión (Presets):**
    - `apply_preset`: Cambia instantáneamente el comportamiento (ej: de "Seguridad" a "Mascotas").
    - `list_presets`: Revisa qué modos tienes disponibles.

2.  **🧠 Estrategia (Fusión):**
    - `set_fusion_strategy`: Decide cómo combinar los múltiples "ojos" (backends).
        - Usa 'consensus' para reducir falsas alarmas (requiere confirmación doble).
        - Usa 'parallel' para detectar todo lo posible.

3.  **🛡️ Zonas de Seguridad:**
    - `create_zone`: Dibuja áreas protegidas basándote en la imagen que ves.
         - Si ves una piscina, crea una zona 'danger' alrededor.
         - Si ves una puerta, crea una zona 'warning'.
    - `delete_zone`: Elimina zonas obsoletas.

4.  **⚙️ Sistema:**
    - `set_system_config`: Ajusta sensibilidad (confianza) o FPS.

## Protocolo de Acción:
1.  **ANALIZA**: Mira la imagen y lee la intención del usuario.
2.  **VERIFICA**: Si te piden un cambio, primero revisa el estado actual (`get_pipeline_status` o `list_zones`).
3.  **EJECUTA**: Llama a la herramienta correspondiente. ¡No tengas miedo de usar las herramientas!
4.  **CONFIRMA**: Dile al usuario qué hiciste.

## Guía Visual:
- Las coordenadas de las zonas son [x, y] de 0.0 a 1.0.
- (0,0) es Arriba-Izquierda.
- (1,1) es Abajo-Derecha.
- Para dibujar un cuadrado centrado: [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]

## Ejemplos de Usuario:
- "Pon el modo de mascotas" -> `apply_preset('pet_monitor')`
- "Avísame si alguien entra a la piscina" -> `create_zone('Piscina', [...], 'danger')`
- "Demasiadas falsas alarmas" -> `set_system_config(confidence_threshold=0.8)` o `set_fusion_strategy('consensus')`
"""

# --- API Models ---

class ChatMessage(BaseModel):
    message: str
    image: Optional[str] = None  # Base64 encoded image
    history: Optional[List[dict]] = None

class ChatResponse(BaseModel):
    response: str
    config_changed: bool = False
    zones_changed: bool = False


# --- Routes ---

@router.post("/chat")
async def chat(request: ChatMessage) -> ChatResponse:
    """Chat with the AI assistant"""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(500, "GEMINI_API_KEY no configurada. Agrégala al archivo .env")
        
        genai.configure(api_key=api_key)
        
        # Tools list for Gemini
        tools = [
            assistant_tools.list_presets,
            assistant_tools.apply_preset,
            assistant_tools.get_pipeline_status,
            assistant_tools.set_fusion_strategy,
            assistant_tools.get_system_config,
            assistant_tools.set_system_config,
            assistant_tools.list_zones,
            assistant_tools.create_zone,
            assistant_tools.delete_zone
        ]

        # Get model name from env
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        
        # Initialize model
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_PROMPT,
            tools=tools
        )
        
        # Build history
        history_content = []
        if request.history:
            for msg in request.history:
                role = "user" if msg.get("role") == "user" else "model"
                history_content.append({"role": role, "parts": [msg.get("content", "")]})
        
        # Start chat session
        chat_session = model.start_chat(
            history=history_content,
            enable_automatic_function_calling=True
        )
        
        # Prepare current message
        message_parts = [request.message]
        if request.image:
            image_data = request.image
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]
            
            import base64
            image_bytes = base64.b64decode(image_data)
            
            message_parts.append({
                "mime_type": "image/jpeg",
                "data": image_bytes
            })
            
        # Send message
        response = chat_session.send_message(message_parts)
        
        # In the new architecture, we don't strictly separate "config_changed" flags
        # because the changes happen immediately via the tools.
        # But we can infer activity if the text response mentions changes.
        # Ideally, we would track tool calls, but the high-level SDK hides them in automatic mode.
        # We'll just return success. The UI will auto-refresh via websocket/polling anyway.
        
        return ChatResponse(
            response=response.text,
            config_changed=True, # Force UI refresh just in case
            zones_changed=True
        )
        
    except Exception as e:
        print(f"Error en chat: {e}")
        # Log full traceback for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error en el asistente: {str(e)}")

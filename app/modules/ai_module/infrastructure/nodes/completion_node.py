"""
Completion node - handles completion and new campaign offers with LLM intelligence
"""

import json
import logging

from langchain_core.messages import AIMessage
from openai import OpenAI

from app.modules.ai_module.infrastructure.conversation_state import ConversationState

logger = logging.getLogger(__name__)
client = OpenAI()

COMPLETION_PROMPT = """
Eres el asistente de finalización de campañas. Tu trabajo es manejar el final exitoso del proceso de creación.

Estado actual:
- Mensaje usuario: "{user_message}"
- Campaña: {campaign_name}
- Evento: {event_name}
- Grupo WhatsApp: {whatsapp_url}
- Estado procesamiento: {processing_status}
- ID del evento: {event_id}

ANÁLISIS DE CONTEXTO:
1. Si completó creación exitosa con grupo listo -> Celebrar y mostrar resumen completo
2. Si usuario pide nueva campaña -> Respuesta entusiasta para reiniciar
3. Si pide resumen/detalles -> Mostrar información de manera amigable
4. Cualquier otro caso -> Respuesta natural apropiada

IMPORTANTE:
- Este nodo solo maneja el final exitoso de creación de campañas
- Las consultas de estado se manejan en otro lugar
- Enfócate en celebrar el éxito y ofrecer nueva campaña

Responde SOLO con JSON:
{{
  "action": "campaign_completed|new_campaign|show_summary|general_response",
  "bot_response": "respuesta completamente natural celebrando el éxito",
  "reset_state": true/false
}}
"""


def completion_node(state: ConversationState) -> dict:
    """Handles completion using LLM intelligence"""
    user_message = state.get("user_message", "")
    logger.info(f"🎉 Completion: '{user_message}'")

    try:
        # Ask LLM what to do
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {"role": "system", "content": COMPLETION_PROMPT.format(
                    user_message=user_message,
                    campaign_name=state.get("campaign_name"),
                    event_name=state.get("event_name"),
                    whatsapp_url=state.get("whatsapp_group_url", "No disponible"),
                    processing_status=state.get("processing_status", "idle"),
                    event_id=state.get("event_id") or state.get("pending_event_id", "No disponible")
                )},
                {"role": "user", "content": user_message}
            ],
            #temperature=0.3
        )
        
        # Robust parse for LLM JSON response
        content = response.output_text
        state["messages"] = AIMessage(content=content, additional_kwargs={"llm": "completion"})

        try:
            llm_response = json.loads(content)
        except Exception:
            try:
                start = content.index("{")
                end = content.rindex("}") + 1
                llm_response = json.loads(content[start:end])
            except Exception as e:
                logger.debug(f"Completion LLM parse error, fallback: {e}")
                llm_response = {
                    "action": "general_response", 
                    "bot_response": "¡Proceso completado! ¿Te gustaría crear una nueva campaña?",
                    "reset_state": False
                }
        
        if llm_response.get("action") == "new_campaign" or llm_response.get("reset_state"):
            # Reset for new campaign
            new_state: ConversationState = {
                "messages": [],
                "campaign_name": None,
                "event_name": None,
                "event_date": None,
                "admins": None,
                "context": None,
                "current_step": "campaign_name",
                "user_message": "",
                "bot_response": "¡Nueva campaña! ¿Cuál será el nombre?",
                "campaign_id": None,
                "event_id": None,
                "whatsapp_group_url": None,
                "processing_status": "idle"
            }
            logger.info("🔄 New campaign started")
            return new_state
        else:
            # Use LLM response
            state["bot_response"] = llm_response.get("bot_response", 
                f"""
🎉 ¡Campaña completada!

📊 Detalles:
• Campaña: {state.get('campaign_name')} ({state.get('campaign_id')})
• Evento: {state.get('event_name')} ({state.get('event_id')})
• Fecha: {state.get('event_date')}
• Grupo: {state.get('whatsapp_group_url') or "En proceso..."}

¿Crear otra campaña? Escribe 'nueva' o 'hola'.
"""
            )
            logger.info("📋 Summary shown")

    except Exception as e:
        logger.error(f"❌ Completion error: {e}")
        state["bot_response"] = "¡Campaña completada! ¿Crear otra? Escribe 'nueva'."

    return state

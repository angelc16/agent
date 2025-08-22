"""
Event creator node - handles event creation with LLM validation
"""

import json
import logging
from openai import OpenAI
import traceback

from app.modules.ai_module.infrastructure.conversation_state import ConversationState
from app.modules.campaign_module.application.campaign_service import LukiaService
from app.modules.campaign_module.domain.exceptions import InvalidEventDate
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)
client = OpenAI()

EVENT_CREATOR_PROMPT = """
Eres el creador de eventos. Recibes datos validados para crear un evento.

Datos del evento:
- Nombre: {event_name}
- Fecha: {event_date}
- Campaign ID: {campaign_id}
- Admins: {admins}
- Contexto: {context}

Valida que:
1. Todos los datos estén completos
2. Los administradores sean números de teléfono válidos
3. El nombre del evento tenga sentido
4. La fecha del evento sea futura y válida

IMPORTANTE: Sobre timezone - Si detectas en el contexto o conversación alguna referencia a una ciudad/país específico, devuelve la timezone en formato "America/Ciudad" (ej: "America/Bogota", "America/Mexico", "America/Lima"). Si no hay información clara, devuelve null.

Si hay algún error o datos inválidos, marca should_create como false y proporciona un mensaje claro al usuario.

Responde SOLO con JSON:
{{
  "should_create": true/false,
  "bot_response": "mensaje al usuario (obligatorio si should_create es false)",
  "next_step": "create_whatsapp_group|error",
  "processing_status": "creating_group|error",
  "timezone": "America/Ciudad|null"
}}
"""


async def event_creator_node(state: ConversationState, lukia_service: LukiaService) -> dict:
    """Creates event using LLM validation"""
    event_name = state.get("event_name")
    logger.info(f"🎪 Creating event: {event_name}")

    try:
        # Ask LLM for validation
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {"role": "system", "content": EVENT_CREATOR_PROMPT.format(
                    event_name=event_name,
                    event_date=state.get("event_date"),
                    campaign_id=state.get("campaign_id"),
                    admins=state.get("admins"),
                    context=state.get("context")
                )},
                {"role": "user", "content": f"Crear evento: {event_name}"}
            ],
            #temperature=0.1
        )
        
        # Robust parse for LLM JSON response
        content = response.output_text
        state["messages"] = AIMessage(content, additional_kwargs={"llm": "event_creator"})

        try:
            llm_response = json.loads(content)
        except Exception:
            try:
                start = content.index("{")
                end = content.rindex("}") + 1
                llm_response = json.loads(content[start:end])
            except Exception as e:
                logger.debug(f"EventCreator LLM parse error, fallback: {e}")
                llm_response = {"should_create": False, "bot_response": "No entendí la validación. Puedes repetir?", "next_step": "error", "processing_status": "error", "timezone": None}

        if llm_response.get("should_create", True):

            # Determine timezone: LLM may return a timezone string, otherwise use default
            timezone = llm_response.get("timezone") or "America/Bogota"

            # Validate event_date before calling service: allow strings but ensure convertible
            event_date_value = state.get("event_date")
            try:
                # Let the service attempt parsing; it will raise InvalidEventDate if bad
                result = await lukia_service.create_event_for_campaign(
                    state.get("campaign_id"),
                    event_name,
                    event_date_value,
                    state.get("admins"),
                    state.get("context"),
                    timezone
                )

            except InvalidEventDate as exc:
                # Use the friendly bot message if available
                bot_message = getattr(exc, 'bot_message', str(exc))
                logger.error(f"❌ Invalid event date: {exc}")
                state["bot_response"] = bot_message
                state["current_step"] = "error"
                state["processing_status"] = "error"
                return state
            except Exception as exc:
                logger.error(traceback.format_exc())
                logger.error(f"❌ Event creation failed before activation: {exc}")
                # Fail fast: set error state and do NOT continue to WhatsApp creation
                state["bot_response"] = (
                    "❌ No pude crear el evento. Por favor revisa los datos y vuelve a intentarlo."
                )
                state["current_step"] = "error"
                state["processing_status"] = "error"
                return state

            if result:
                state["event_id"] = result.id
                state["bot_response"] = f"✅ Evento '{event_name}' creado. Creando grupo WhatsApp..."
                state["current_step"] = "create_whatsapp_group"
                state["processing_status"] = "creating_group"
                logger.info(f"✅ Event created: {state['event_id']}")
            else:
                state["bot_response"] = "❌ Error al crear el evento."
                state["current_step"] = "error"
                state["processing_status"] = "error"
        else:
            state["bot_response"] = llm_response.get("bot_response", "Error en validación")
            state["current_step"] = llm_response.get("next_step", "error")
            state["processing_status"] = llm_response.get("processing_status", "error")

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"❌ Event creation error: {e}")
        state["bot_response"] = f"❌ Error técnico: {str(e)}"
        state["current_step"] = "error"
        state["processing_status"] = "error"

    return state

"""
WhatsApp group creator node - handles WhatsApp group creation with LLM intelligence
"""

import json
import logging
import traceback
from openai import OpenAI
from langchain_core.messages import AIMessage

from app.modules.ai_module.infrastructure.conversation_state import ConversationState
from app.modules.campaign_module.application.campaign_service import LukiaService

logger = logging.getLogger(__name__)
client = OpenAI()

WHATSAPP_CREATOR_PROMPT = """
Eres el activador de grupos de WhatsApp. Tu trabajo es activar el evento para que se genere el grupo.

Información disponible:
- Event ID: {event_id}

Análisis simple:
1. Si hay event_id válido -> activar evento (esto genera el grupo automáticamente)
2. Si no hay event_id -> reportar error

El servicio activate_event() solo necesita el event_id y se encarga de todo el proceso de creación del grupo.

Responde SOLO con JSON:
{{
  "should_activate": true/false,
  "bot_response": "mensaje al usuario sobre la activación",
  "next_step": "pending_group|error",
  "processing_status": "completed|error"
}}
"""


async def whatsapp_group_creator_node(state: ConversationState, lukia_service: LukiaService) -> dict:
    """Activates event to trigger WhatsApp group creation"""
    event_id = state.get("event_id")
    logger.info(f"💬 Activating event {event_id} to create WhatsApp group")
    # If prior node failed or event_id missing, fail fast and report error
    if state.get("processing_status") != "creating_group" or not event_id:
        logger.info("WhatsApp creator skipped because prior step failed or event_id missing")
        state["bot_response"] = "❌ No se puede crear el grupo porque no existe un evento válido."
        state["current_step"] = "error"
        state["processing_status"] = "error"
        return state
    try:
        # Ask LLM for guidance
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {"role": "system", "content": WHATSAPP_CREATOR_PROMPT.format(
                    event_id=event_id
                )},
                {"role": "user", "content": f"Activar evento {event_id} para generar grupo WhatsApp"}
            ],
            #temperature=0.1
        )

        # Robust parse for LLM JSON response
        content = response.output_text
        state["messages"] = AIMessage(content, additional_kwargs={"llm": "whatsapp_group_creator"})
        try:
            llm_response = json.loads(content)
        except Exception:
            try:
                start = content.index("{")
                end = content.rindex("}") + 1
                llm_response = json.loads(content[start:end])
            except Exception as e:
                logger.debug(f"WhatsAppCreator LLM parse error, fallback: {e}")
                llm_response = {"should_activate": True, "bot_response": "Activando evento para generar grupo.", "next_step": "pending_group", "processing_status": "completed"}

        if llm_response.get("should_activate", True) and event_id:
            # Activate event - this triggers WhatsApp group creation automatically
            response = await lukia_service.activate_event(event_id)
            logger.info(f"Event activation response: {response}")
            
            # Record pending event id so status can be checked later
            state["pending_event_id"] = event_id

            # Use LLM response if available, otherwise fallback to default message
            state["bot_response"] = llm_response.get("bot_response", 
                "✅ Evento activado correctamente. "
                "El grupo de WhatsApp se está generando en segundo plano. "
                "En unos momentos estará listo y podrás consultar el enlace."
            )
            state["current_step"] = llm_response.get("next_step", "pending_group")
            state["processing_status"] = llm_response.get("processing_status", "completed")
            logger.info("✅ Event activated - WhatsApp group creation in progress")
        else:
            state["bot_response"] = llm_response.get("bot_response", "Error en creación de grupo")
            state["current_step"] = llm_response.get("next_step", "error")
            state["processing_status"] = llm_response.get("processing_status", "error")

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"❌ WhatsApp creation error: {e}")
        state["bot_response"] = f"❌ Error creando grupo: {str(e)}"
        state["current_step"] = "error"
        state["processing_status"] = "error"

    return state

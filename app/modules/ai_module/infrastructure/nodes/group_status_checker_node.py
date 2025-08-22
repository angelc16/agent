"""
Group status checker node - handles WhatsApp group status checking with LLM intelligence
"""

import json
import logging
from openai import OpenAI
from langchain_core.messages import AIMessage

from app.modules.ai_module.infrastructure.conversation_state import ConversationState
from app.modules.campaign_module.application.campaign_service import LukiaService

logger = logging.getLogger(__name__)
client = OpenAI()

STATUS_CHECKER_PROMPT = """
Eres el verificador de estado de grupos WhatsApp. El usuario pregunta sobre el estado de un evento/grupo.

Contexto:
- Mensaje usuario: "{user_message}"
- Event ID disponible: {event_id}
- Estado actual: {processing_status}

Analiza el mensaje y decide:
1. Si pregunta por estado y hay event_id -> verificar grupo
2. Si pregunta por estado pero no hay event_id -> pedir SOLO el event_id
3. Si dice otra cosa -> responder apropiadamente
4. Si hay problema -> reportar error

IMPORTANTE: Si no hay event_id disponible, pide al usuario que proporcione ÚNICAMENTE el ID del evento. Hazlo de forma amable y natural, por ejemplo: "Para poder verificar el estado, ¿podrías darme el ID del evento? 😊"

Responde SOLO con JSON:
{{
  "should_check": true/false,
  "bot_response": "respuesta al usuario si NO debe verificar",
  "next_step": "completed|wait|error",
  "processing_status": "completed|pending|error"
}}
"""

STATUS_RESPONSE_PROMPT = """
Eres el generador de respuestas para consultas de estado de grupos WhatsApp.

Situación:
- Mensaje usuario: "{user_message}"
- Event ID: {event_id}
- Estado encontrado: {status_result}
- Link del grupo: {group_link}
- Error: {error_message}

Genera una respuesta natural y humana según el resultado:

1. Si hay link disponible -> Celebrar y entregar el link de forma amigable
2. Si grupo está pendiente -> Explicar que está en proceso y dar tiempo estimado
3. Si no se encontró -> Explicar que el grupo aún puede estar pendiente o que el ID podría ser incorrecto, de forma amable
4. Si hubo error -> Disculparse y sugerir reintentar

EJEMPLOS DE BUENAS RESPUESTAS:
- "¡Perfecto! 🎉 Tu grupo está listo: [link]. ¡Ya puedes compartirlo con tus invitados!"
- "⏳ Tu grupo se está generando. Normalmente toma unos 2-3 minutos. ¿Puedes consultar en un momento?"
- "No encontré un grupo para ese evento. ¿Podrías verificar el ID?"

Responde SOLO con JSON:
{{
  "bot_response": "respuesta completamente natural y humana",
  "current_step": "completed|wait|error",
  "processing_status": "completed|pending|error"
}}
"""


def _parse_llm_response(content: str, fallback_response: dict) -> dict:
    """Parse LLM JSON response with robust fallback"""
    try:
        return json.loads(content)
    except Exception:
        try:
            start = content.index("{")
            end = content.rindex("}") + 1
            return json.loads(content[start:end])
        except Exception as e:
            logger.debug(f"LLM parse error, using fallback: {e}")
            return fallback_response


def _should_check_status(user_message: str, event_id: str, processing_status: str) -> dict:
    """Ask LLM if we should check status"""
    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "system",
                    "content": STATUS_CHECKER_PROMPT.format(
                        user_message=user_message,
                        event_id=event_id or "No disponible",
                        processing_status=processing_status,
                    ),
                },
                {"role": "user", "content": user_message},
            ],
        )
        
        fallback = {
            "should_check": True,
            "bot_response": "Verificaré el estado del grupo.",
            "next_step": "wait",
            "processing_status": "pending",
        }
        return _parse_llm_response(response.output_text, fallback)
    except Exception as e:
        logger.error(f"Error asking LLM for status check decision: {e}")
        return {
            "should_check": False,
            "bot_response": "No puedo verificar el estado en este momento. Intenta más tarde.",
            "next_step": "error",
            "processing_status": "error"
        }


async def _get_group_status(lukia_service: LukiaService, event_id: str) -> tuple:
    """Get group status from API and return (status_result, group_link, error_message)"""
    try:
        group_status = await lukia_service.get_group_status(event_id)
        
        if group_status and hasattr(group_status, "link") and group_status.link:
            return "ready", group_status.link, ""
        elif group_status:
            return "pending", "No disponible", ""
        else:
            return "not_found", "No disponible", ""
            
    except Exception as e:
        logger.error(f"API error checking group status: {e}")
        return "error", "No disponible", "Error interno"


def _generate_status_response(user_message: str, event_id: str, status_result: str, group_link: str, error_message: str) -> dict:
    """Generate human response based on status result"""
    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "system",
                    "content": STATUS_RESPONSE_PROMPT.format(
                        user_message=user_message,
                        event_id=event_id,
                        status_result=status_result,
                        group_link=group_link,
                        error_message=error_message,
                    ),
                },
                {
                    "role": "user",
                    "content": f"Generar respuesta para consulta de estado: {status_result}",
                },
            ],
        )
        
        # Fallback responses based on status
        fallback_responses = {
            "ready": {
                "bot_response": f"¡Perfecto! 🎉 Tu grupo está listo: {group_link}",
                "current_step": "completed",
                "processing_status": "completed",
            },
            "pending": {
                "bot_response": "⏳ Tu grupo se está generando. Consulta en unos momentos.",
                "current_step": "wait",
                "processing_status": "pending",
            },
            "not_found": {
                "bot_response": "No encontré un grupo para ese evento. ¿Podrías verificar el ID?",
                "current_step": "error",
                "processing_status": "error",
            },
            "error": {
                "bot_response": "Hubo un problema consultando el estado. Intenta de nuevo en unos momentos.",
                "current_step": "error", 
                "processing_status": "error",
            }
        }
        
        fallback = fallback_responses.get(status_result, fallback_responses["error"])
        return _parse_llm_response(response.output_text, fallback)
        
    except Exception as e:
        logger.error(f"Error generating status response: {e}")
        return {
            "bot_response": "No puedo generar una respuesta en este momento.",
            "current_step": "error",
            "processing_status": "error"
        }


async def group_status_checker_node(state: ConversationState, lukia_service: LukiaService) -> dict:
    """Checks WhatsApp group status using LLM intelligence"""
    user_message = state.get("user_message", "")
    event_id = state.get("event_id") or state.get("pending_event_id")
    logger.info(f"🔍 Status check: '{user_message}' for event {event_id}")

    try:
        # Step 1: Ask LLM if we should check status
        decision = _should_check_status(user_message, event_id, state.get("processing_status"))

        if decision.get("should_check", True) and event_id:
            # Step 2: Get status from API
            status_result, group_link, error_message = await _get_group_status(lukia_service, event_id)

            # Step 3: Update state if group is ready
            if status_result == "ready":
                state["whatsapp_group_url"] = group_link
                state["came_from_status_check"] = True

            # Step 4: Generate human response
            response_data = _generate_status_response(
                user_message, event_id, status_result, group_link, error_message
            )

            # Apply response to state
            state["bot_response"] = response_data.get("bot_response", "Estado consultado.")
            state["current_step"] = response_data.get("current_step", "wait")
            state["processing_status"] = response_data.get("processing_status", "pending")

            logger.info(f"✅ Status check result: {status_result} - {state['current_step']}")

        else:
            # LLM decided not to check or no event_id available
            state["bot_response"] = decision.get("bot_response", "Para consultar el estado, necesito el ID del evento. ¿Podrías proporcionármelo?")
            state["current_step"] = decision.get("next_step", "wait")
            state["processing_status"] = decision.get("processing_status", "pending")

        # Always set messages for LangGraph
        state["messages"] = AIMessage(state["bot_response"], additional_kwargs={"llm": "group_status_checker"})

    except Exception as e:
        logger.error(f"Unexpected error in status checker: {e}")
        state["bot_response"] = "No puedo consultar el estado en este momento. Intenta más tarde."
        state["current_step"] = "error"
        state["processing_status"] = "error"
        state["messages"] = AIMessage(state["bot_response"], additional_kwargs={"llm": "group_status_checker"})

    return state

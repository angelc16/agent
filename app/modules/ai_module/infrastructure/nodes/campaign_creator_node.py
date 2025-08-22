"""
Campaign creator node - handles campaign creation with LLM validation
"""

import json
import logging
import traceback
from datetime import datetime

from langchain_core.messages import AIMessage
from openai import OpenAI

from app.core.config.settings import settings
from app.modules.ai_module.infrastructure.conversation_state import ConversationState
from app.modules.campaign_module.application.campaign_service import LukiaService
from app.modules.campaign_module.infrastructure.lukia_api_client import LukiaAPIClient

logger = logging.getLogger(__name__)
client = OpenAI()

CAMPAIGN_CREATOR_PROMPT = """
Eres el creador de campañas. Recibes datos validados y debes crear una campaña.

Datos de la campaña:
- Nombre: {campaign_name}
- Estado: {processing_status}

Tu trabajo es:
1. Validar que los datos están completos
2. Crear la campaña usando la API
3. Responder al usuario sobre el resultado

Si algo falla, explica el error de manera amigable.

Responde SOLO con JSON:
{{
  "should_create": true/false,
  "bot_response": "mensaje al usuario",
  "next_step": "create_event|error",
  "processing_status": "creating_event|error"
}}
"""


async def campaign_creator_node(
    state: ConversationState, lukia_service: LukiaService
) -> dict:
    """Creates campaign using LLM validation"""
    campaign_name = state.get("campaign_name")
    logger.info(f"🏢 Creating campaign: {campaign_name}")

    try:
        # Ask LLM for validation and guidance
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "system",
                    "content": CAMPAIGN_CREATOR_PROMPT.format(
                        campaign_name=campaign_name,
                        processing_status=state.get("processing_status"),
                    ),
                },
                {"role": "user", "content": f"Crear campaña: {campaign_name}"},
            ],
            # temperature=0.1
        )

        llm_response = json.loads(response.output_text)
        state["messages"] = AIMessage(content=response.output_text, additional_kwargs={"llm": "campaign_creator"})

        if llm_response.get("should_create", True):
            result = await lukia_service.create_campaign_with_defaults(campaign_name)

            if result:
                logger.info(f"✅ Campaign created: {result.id} {result}")
                state["campaign_id"] = result.id
                state["bot_response"] = (f"✅ Campaña '{campaign_name}' creada. Creando evento...")
                state["current_step"] = "create_event"
                state["processing_status"] = "creating_event"
                logger.info(f"✅ Campaign created: {state['campaign_id']}")
            else:
                state["bot_response"] = (
                    "❌ Error al crear la campaña. ¿Intentamos de nuevo?"
                )
                state["current_step"] = "error"
                state["processing_status"] = "error"
        else:
            state["bot_response"] = llm_response.get(
                "bot_response", "Error en validación"
            )
            state["current_step"] = llm_response.get("next_step", "error")
            state["processing_status"] = llm_response.get("processing_status", "error")

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"❌ Campaign creation error: {e}")
        state["bot_response"] = f"❌ Error técnico: {str(e)}"
        state["current_step"] = "error"
        state["processing_status"] = "error"

    return state

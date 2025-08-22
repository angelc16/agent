"""
CampaignBotStateGraph - Main class that orchestrates the modular campaign bot
"""

import logging
from typing import Dict, Any, Optional

from langgraph.checkpoint.memory import InMemorySaver

from app.modules.ai_module.infrastructure.conversation_state import ConversationState
from app.modules.campaign_module.application.campaign_service import LukiaService
from app.modules.campaign_module.infrastructure.lukia_api_client import LukiaAPIClient
from app.modules.ai_module.infrastructure.graph.builder import build_campaign_graph

logger = logging.getLogger(__name__)


class CampaignBotStateGraph:
    """
    SINGLE StateGraph implementation for campaign creation with specialized nodes.
    Each node has one responsibility following microservices architecture.
    """

    def __init__(self):
        self.lukia_api = LukiaAPIClient()
        self.campaign_service = LukiaService()
        # Initialize in-memory checkpointer for state persistence
        self.checkpointer = InMemorySaver()
        self.graph = build_campaign_graph(self.campaign_service, self.checkpointer)

    async def process_message(
        self,
        user_message: str,
        user_id: str,
        session_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process message through the SINGLE StateGraph with persistence"""
        try:
            # Use user_id as thread_id for persistence
            config = {"configurable": {"thread_id": user_id}}
            message = {
                "messages": [{"role": "user", "content": user_message}],
                "user_message": user_message
            }
            result = await self.graph.ainvoke(message, config)
            logger.info(f"Graph execution completed for user {user_id}")
            return result  # result is already a dict

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "bot_response": f"❌ Error: {str(e)}",
                "current_step": "error",
                "processing_status": "error",
            }

    def get_user_state(self, user_id: str) -> Dict[str, Any]:
        """Get the current state for a specific user"""
        try:
            config = {"configurable": {"thread_id": user_id}}
            state = self.graph.get_state(config)
            return state.values if state.values else {}
        except Exception as e:
            logger.error(f"Error getting state for user {user_id}: {e}")
            return {}

    def get_user_state_history(self, user_id: str) -> list:
        """Get the state history for a specific user"""
        try:
            config = {"configurable": {"thread_id": user_id}}
            return list(self.graph.get_state_history(config))
        except Exception as e:
            logger.error(f"Error getting state history for user {user_id}: {e}")
            return []

    def reset_user_state(self, user_id: str) -> bool:
        """Reset the state for a specific user (useful for starting over)"""
        try:
            config = {"configurable": {"thread_id": user_id}}
            # Create a fresh initial state
            initial_state: ConversationState = {
                "messages": [],
                "campaign_name": None,
                "event_name": None,
                "event_date": None,
                "admins": None,
                "context": None,
                "current_step": "greeting",
                "user_message": "",
                "bot_response": "¡Hola! Soy tu asistente para crear campañas con eventos y grupos de WhatsApp. ¿Cómo te llamas y qué campaña quieres crear?",
                "campaign_id": None,
                "event_id": None,
                "whatsapp_group_url": None,
                "processing_status": "idle"
            }
            # This will overwrite the existing state
            self.graph.update_state(config, initial_state)
            logger.info(f"Reset state for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting state for user {user_id}: {e}")
            return False

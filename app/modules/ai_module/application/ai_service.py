"""AI service for handling campaign conversations."""

from typing import Dict, Optional

from app.modules.ai_module.infrastructure.campaign_graph import CampaignBotStateGraph


class AIService:
    """Service for handling AI-powered campaign conversations."""

    def __init__(self):
        self.state_graph = CampaignBotStateGraph()
        self.user_sessions: Dict[str, Dict] = {}  # Store as dict directly

    async def process_user_message(self, user_id: str, message: str) -> dict:
        """Process a user message and return a response."""
        try:
            # Process through StateGraph with correct parameters
            updated_state = await self.state_graph.process_message(
                user_message=message,
                user_id=user_id,
            )

            # Store updated state
            self.user_sessions[user_id] = updated_state

            # Return response
            return {
                "success": True,
                "message": updated_state.get("bot_response", ""),
                "user_id": user_id,
                "session_data": updated_state,
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "message": "Lo siento, ocurrió un error procesando tu mensaje. ¿Puedes intentar de nuevo?",
                "user_id": user_id,
                "session_data": None,
                "error": str(e)
            }

    def get_user_session(self, user_id: str) -> Optional[dict]:
        """Get current session data for a user."""
        state = self.state_graph.get_user_state(user_id)
        if state:
            return state
        return None

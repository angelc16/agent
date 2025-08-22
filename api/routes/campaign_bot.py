"""Campaign bot API routes with LangGraph integration."""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api.schemas.campaign_bot import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationStatusResponse,
    GroupStatusRequest,
    GroupStatusResponse,
    ResetConversationResponse,
)
from app.modules.ai_module.application.ai_service import AIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Campaign Bot"])

# Global AI service instance
_ai_service = None


def get_ai_service() -> AIService:
    """Dependency injection for the AI service."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    ai_service: AIService = Depends(get_ai_service),
) -> ChatMessageResponse:
    """Send a message to the campaign bot."""
    try:
        # Process message through LangGraph
        response = await ai_service.process_user_message(
            user_id=request.user_id,
            message=request.message
        )

        if not response["success"]:
            raise HTTPException(
                status_code=500,
                detail=response.get("error", "Failed to process message")
            )

        # Map response to expected format
        return ChatMessageResponse(
            message=response["message"],
            state="active",  # Simplified state for now
            requires_input=True,  # Always require input in conversation
            metadata=response.get("session_data", {}),
        )

    except Exception as e:
        logger.error(f"Error processing message for user {request.user_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to process message"
        ) from e


@router.get("/status/{user_id}")
async def get_conversation_status(
    user_id: str,
    ai_service: AIService = Depends(get_ai_service),
) -> ConversationStatusResponse:
    """Get the current conversation status for a user."""
    try:
        session_data = ai_service.get_user_session(user_id)

        if not session_data:
            return JSONResponse(content={"message": "No active session"}, status_code=200)

        return JSONResponse(content=jsonable_encoder(session_data), status_code=200)

    except Exception as e:
        logger.error(f"Error getting status for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to get conversation status"
        ) from e


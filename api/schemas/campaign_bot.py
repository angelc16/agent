"""API schemas for the campaign bot."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request model for chat messages."""

    user_id: str = Field(..., description="User identifier", min_length=1)
    message: str = Field(..., description="User message", min_length=1)


class ChatMessageResponse(BaseModel):
    """Response model for chat messages."""

    message: str = Field(..., description="Bot response message")
    state: str = Field(..., description="Current conversation state")
    requires_input: bool = Field(..., description="Whether bot expects user input")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional response metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )


class ConversationStatusResponse(BaseModel):
    """Response model for conversation status."""

    status: str = Field(..., description="Conversation status")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Detailed conversation information"
    )


class GroupStatusRequest(BaseModel):
    """Request model for checking group status."""

    group_id: str = Field(..., description="WhatsApp group ID", min_length=1)


class GroupStatusResponse(BaseModel):
    """Response model for group status."""

    group_id: str = Field(..., description="WhatsApp group ID")
    status: str = Field(..., description="Group status")
    link: Optional[str] = Field(default=None, description="WhatsApp group link")
    message: str = Field(..., description="Status message")
    ready: bool = Field(..., description="Whether group is ready")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Error timestamp"
    )


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Health check timestamp"
    )
    version: str = Field(default="1.0.0", description="API version")


class ResetConversationResponse(BaseModel):
    """Response model for conversation reset."""

    success: bool = Field(..., description="Whether reset was successful")
    message: str = Field(..., description="Reset confirmation message")

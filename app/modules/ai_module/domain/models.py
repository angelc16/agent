"""AI domain models and data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationState(str, Enum):
    """States of the campaign creation conversation."""

    INITIAL = "initial"
    GATHERING_CAMPAIGN_INFO = "gathering_campaign_info"
    GATHERING_EVENT_INFO = "gathering_event_info"
    GATHERING_EVENT_DATE = "gathering_event_date"
    GATHERING_ADMINISTRATORS = "gathering_administrators"
    GATHERING_CONTEXT = "gathering_context"
    CONFIRMING_DETAILS = "confirming_details"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class UserMessage(BaseModel):
    """User message structure."""

    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="User message content")
    timestamp: datetime = Field(default_factory=datetime.now)


class BotResponse(BaseModel):
    """Bot response structure."""

    message: str = Field(..., description="Bot response message")
    state: ConversationState = Field(..., description="Current conversation state")
    requires_input: bool = Field(
        default=True, description="Whether bot expects user input"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional response metadata"
    )


class CampaignContext(BaseModel):
    """Context information for campaign creation."""

    campaign_name: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[datetime] = None
    administrators: Optional[List[str]] = None
    context: Optional[str] = None
    timezone: str = "America/Bogota"
    confirmed: bool = False

class CampaignCreationResult(BaseModel):
    """Result of campaign creation process."""

    success: bool = Field(..., description="Whether creation was successful")
    campaign_id: Optional[str] = Field(default=None, description="Created campaign ID")
    event_id: Optional[str] = Field(default=None, description="Created event ID")
    whatsapp_groups: List[str] = Field(
        default_factory=list, description="WhatsApp group links"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    message: str = Field(..., description="User-friendly message")

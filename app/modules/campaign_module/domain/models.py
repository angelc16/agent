from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CampaignInput(BaseModel):
    """Input model for creating a campaign."""

    name: str = Field(..., description="Campaign name")
    company_id: str = Field(..., description="Company ID")
    integration_id: str = Field(..., description="Integration ID")
    external_campaign_id: Optional[str] = Field(
        default=None, description="External campaign identifier"
    )
    metadata: Optional[Dict] = Field(default=None, description="Additional metadata")


class Campaign(BaseModel):
    """Campaign model."""
    id: Optional[str] = Field(default=None, alias="_id", description="Campaign ID")
    name: str = Field(..., description="Campaign name")
    company_id: str = Field(..., description="Company ID")
    integration_id: str = Field(..., description="Integration ID")
    external_campaign_id: Optional[str] = Field(
        default=None, description="External campaign identifier"
    )
    metadata: Optional[Dict] = Field(default=None, description="Additional metadata")
    created_at: Optional[datetime] = Field(
        default=None, description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )


class EventInput(BaseModel):
    """Input model for creating an event."""

    name: str = Field(..., description="Event name")
    campaign_id: str = Field(..., description="Associated campaign ID")
    event_date: datetime = Field(..., description="Event date and time")
    timezone: str = Field(default="America/Bogota", description="Event timezone")
    administrators: List[str] = Field(
        ..., description="List of administrator phone numbers"
    )
    image_url: Optional[str] = Field(
        default=None, description="Event image URL or base64"
    )
    context: Optional[str] = Field(default=None, description="Event context/details")
    metadata: Optional[Dict] = Field(default=None, description="Additional metadata")


class Event(BaseModel):
    """Event model."""

    id: Optional[str] = Field(default=None, description="Event ID")
    name: str = Field(..., description="Event name")
    campaign_id: str = Field(..., description="Associated campaign ID")
    event_date: datetime = Field(..., description="Event date and time")
    timezone: str = Field(default="America/Bogota", description="Event timezone")
    administrators: List[str] = Field(
        ..., description="List of administrator phone numbers"
    )
    image_url: Optional[str] = Field(
        default=None, description="Event image URL or base64"
    )
    context: Optional[str] = Field(default=None, description="Event context/details")
    metadata: Optional[Dict] = Field(default=None, description="Additional metadata")
    status: str = Field(default="draft", description="Event status")
    created_at: Optional[datetime] = Field(
        default=None, description="Creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )


class MessageGroup(BaseModel):
    """WhatsApp group model."""

    id: Optional[str] = Field(default=None, description="Group ID")
    event_id: str = Field(..., description="Associated event ID")
    external_id: Optional[str] = Field(
        default=None, description="External WhatsApp group ID"
    )
    link: Optional[str] = Field(default=None, description="WhatsApp group link")
    status: str = Field(default="pending", description="Group status")
    capacity: int = Field(default=0, description="Group capacity")
    current_participants: int = Field(
        default=0, description="Current number of participants"
    )
    created_at: Optional[datetime] = Field(
        default=None, description="Creation timestamp"
    )

"""
ConversationState class for managing campaign bot state
"""

from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationState(TypedDict):
    # User information
    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str = ""

    # Process status
    current_step: str = "greeting"
    processing_status: str = (
        "idle"  # idle, creating_campaign, creating_event, creating_group
    )

    # Campaign data collection
    campaign_name: Optional[str] = None
    event_name: Optional[str] = None
    event_date: Optional[str] = None
    admins: Optional[list] = None
    context: Optional[str] = None
    timezone: Optional[str] = None

    # External API results
    campaign_id: Optional[str] = None
    event_id: Optional[str] = None
    pending_event_id: Optional[str] = None
    whatsapp_group_url: Optional[str] = None
    came_from_status_check: Optional[bool] = None
    
    # Response to user
    bot_response: str = ""

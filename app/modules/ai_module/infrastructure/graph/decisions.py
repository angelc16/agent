"""
Decision functions for the campaign graph nodes
"""

import logging

from app.modules.ai_module.infrastructure.conversation_state import ConversationState

logger = logging.getLogger(__name__)


def router_decision(state: ConversationState) -> str:
    """Decision function for router - determines next action"""
    current_step = state.get("current_step", "greeting")
    processing_status = state.get("processing_status", "idle")

    logger.info(f"Router decision: step={current_step}, status={processing_status}")

    # If message is out of context, end the flow
    if current_step == "out_of_context" or processing_status == "out_of_context":
        logger.info("Router decision: out of context message - ending flow")
        return "__end__"

    # If user wants to check group status directly
    if current_step == "check_status":
        return "check_status"

    # If processing_status indicates campaign creation, route to campaign_creator
    # Accept either 'create_campaign' or 'creating_campaign' as current_step values
    if processing_status == "creating_campaign":
        return "create_campaign"

    # Backwards-compatible: explicit create_campaign step name
    if current_step == "create_campaign" and processing_status == "idle":
        return "create_campaign"

    # If we're waiting for whatsapp_link
    if current_step == "pending_group":
        return "pending_group"

    # If process is completed
    if current_step == "completed":
        return "completed"

    # If there's an error
    if current_step == "error":
        return "error"

    # For conversation steps, END the flow and wait for next user message
    if current_step in [
        "greeting",
        "campaign_name",
        "event_name",
        "event_date",
        "timezone",
        "admins",
        "context",
        "confirmation",
    ]:
        return "__end__"

    # Default: END
    logger.warning(
        f"Router decision: unexpected state, ending. Step: {current_step}"
    )
    return "__end__"


def event_creator_decision(state: ConversationState) -> str:
    """Decision function for event creator - determines if creation succeeded"""
    current_step = state.get("current_step", "error")
    processing_status = state.get("processing_status", "error")

    logger.info(f"Event creator decision: step={current_step}, status={processing_status}")

    # If event was created successfully, proceed to WhatsApp group creation
    if current_step == "create_whatsapp_group" and processing_status == "creating_group":
        return "create_whatsapp_group"
    
    # If there was an error, end the flow (user will see the error message)
    if current_step == "error" or processing_status == "error":
        return "error"
    
    # Default: error
    logger.warning(f"Event creator decision: unexpected state, error. Step: {current_step}")
    return "error"


def whatsapp_decision(state: ConversationState) -> str:
    """Decision function for WhatsApp group creator"""
    processing_status = state.get("processing_status", "idle")

    logger.info(f"WhatsApp decision: status={processing_status}")

    # If group was created successfully (has link), go to completion
    if processing_status == "completed" or processing_status == "creating":
        return "completed"
    # If group is pending (async), go directly to status checker
    # if processing_status == "pending":
    #     return "pending"
    return "error"


def status_decision(state: ConversationState) -> str:
    """Decision function for status checker"""
    processing_status = state.get("processing_status", "idle")

    logger.info(f"Status decision: status={processing_status}")

    if processing_status == "completed":
        return "completed"
    if processing_status == "error":
        return "error"
    return "wait"


def completion_decision(state: ConversationState) -> str:
    """Decision function for completion node - always ends"""
    logger.info("Completion decision: always ending flow")
    # Completion always ends the flow to prevent recursion
    return "end"

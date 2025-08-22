"""
Graph builder for campaign bot - creates and configures the StateGraph
"""

import logging
from functools import partial

from langgraph.graph import END, StateGraph

from app.modules.ai_module.infrastructure.conversation_state import ConversationState
from app.modules.ai_module.infrastructure.graph.decisions import (
    completion_decision,
    event_creator_decision,
    router_decision,
    status_decision,
    whatsapp_decision,
)
from app.modules.ai_module.infrastructure.nodes.campaign_creator_node import (
    campaign_creator_node,
)
from app.modules.ai_module.infrastructure.nodes.completion_node import completion_node
from app.modules.ai_module.infrastructure.nodes.event_creator_node import (
    event_creator_node,
)
from app.modules.ai_module.infrastructure.nodes.group_status_checker_node import (
    group_status_checker_node,
)
from app.modules.ai_module.infrastructure.nodes.router_node import router_node
from app.modules.ai_module.infrastructure.nodes.whatsapp_group_creator_node import (
    whatsapp_group_creator_node,
)
from app.modules.campaign_module.application.campaign_service import LukiaService
from app.modules.campaign_module.infrastructure.lukia_api_client import LukiaAPIClient

logger = logging.getLogger(__name__)


def build_campaign_graph(lukia_service: LukiaService, checkpointer=None) -> StateGraph:
    """Builds the LangGraph StateGraph with specialized nodes"""

    # Create the graph with state schema
    graph = StateGraph(ConversationState)

    # Create partial functions with lukia_service bound for async nodes
    campaign_creator_with_api = partial(campaign_creator_node, lukia_service=lukia_service)
    event_creator_with_api = partial(event_creator_node, lukia_service=lukia_service)
    whatsapp_creator_with_api = partial(
        whatsapp_group_creator_node, lukia_service=lukia_service
    )
    status_checker_with_api = partial(group_status_checker_node, lukia_service=lukia_service)

    # Add specialized nodes
    graph.add_node("router", router_node)
    graph.add_node("campaign_creator", campaign_creator_with_api)
    graph.add_node("event_creator", event_creator_with_api)
    graph.add_node("whatsapp_group_creator", whatsapp_creator_with_api)
    graph.add_node("group_status_checker", status_checker_with_api)
    graph.add_node("completion", completion_node)

    # Define the workflow
    graph.set_entry_point("router")

    # Router decides next step
    graph.add_conditional_edges(
        "router",
        router_decision,
        {
            "create_campaign": "campaign_creator",
            "check_status": "group_status_checker",
            "pending_group": END,
            "completed": "completion",
            "__end__": END,
            "error": END,
        },
    )

    # Linear flow for creation
    graph.add_edge("campaign_creator", "event_creator")
    
    # Event creator decides next step based on success/failure
    graph.add_conditional_edges(
        "event_creator",
        event_creator_decision,
        {
            "create_whatsapp_group": "whatsapp_group_creator",
            "error": END,
        },
    )

    # WhatsApp group can go to completion or status checker
    graph.add_conditional_edges(
        "whatsapp_group_creator",
        whatsapp_decision,
        {
            # "completed": "completion",
            "completed": END,
            "error": END,
        },
    )

    # Status checker can complete or wait
    graph.add_conditional_edges(
        "group_status_checker",
        status_decision,
        {"completed": END, "wait": END, "error": END},
    )

    # Completion always ends
    graph.add_conditional_edges("completion", completion_decision, {"end": END})

    # Compile with checkpointer if provided
    return graph.compile(checkpointer=checkpointer)

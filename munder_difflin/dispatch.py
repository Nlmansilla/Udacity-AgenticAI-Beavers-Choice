"""Route validated customer requests to specialist agents."""

import json
from typing import List

from .agents import get_default_agent_system
from .catalog_matching import build_order_items, resolve_catalog_items
from .schemas import CatalogMatch, CustomerRequest


def dispatch_request(
    request: CustomerRequest,
    matches: List[CatalogMatch] | None = None,
    agent_system=None,
) -> str:
    """Route a validated customer request to the appropriate specialist."""
    if agent_system is None:
        agent_system = get_default_agent_system()

    if request.clarification_needed:
        return request.clarification_needed

    try:
        if matches is None:
            matches = resolve_catalog_items(
                request.items, agent_system.orchestrator_agent
            )
        order_items = build_order_items(request.items, matches)
    except ValueError as error:
        return f"{error} No order has been placed."

    # Keep the original typed request intact; specialists receive canonical items.
    specialist_payload = request.model_dump(mode="json")
    specialist_payload["items"] = [item.model_dump() for item in order_items]
    specialist_message = json.dumps(specialist_payload)

    if request.intent == "quote":
        if not request.items:
            return "Which products and quantities would you like quoted?"

        result = agent_system.quote_agent.run_sync(specialist_message)
        return result.output

    if request.intent == "inventory":
        result = agent_system.inventory_agent.run_sync(specialist_message)
        return result.output

    if request.intent == "purchase":
        if not request.items:
            return "Which products and quantities would you like to order?"

        if request.delivery_due_date is None:
            return "By what date do you need the order?"

        if not request.order_id or not request.order_id.strip():
            raise ValueError(
                "The application must supply an order ID before execution."
            )

        result = agent_system.sales_agent.run_sync(specialist_message)
        return result.output

    if request.intent == "report":
        result = agent_system.reporting_agent.run_sync(specialist_message)
        return result.output

    return "This request type is not yet supported by the dispatcher."

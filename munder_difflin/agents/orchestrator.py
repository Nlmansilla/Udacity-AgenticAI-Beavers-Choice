"""Construct the orchestrator Pydantic AI agent."""

from pydantic_ai import Agent

from ..schemas import ParsedCustomerRequest


def build_orchestrator_agent(model) -> Agent:
    """Build and return this worker agent."""
    return Agent(
        model=model,
        output_type=ParsedCustomerRequest,
        instructions=(
            "Interpret customer requests for a paper supply company. Classify "
            "the intent as inventory, quote, purchase, or report. Use purchase "
            "only for explicit instructions to place an order; a price or "
            "availability inquiry is not a purchase. Extract product names, "
            "quantities, and any delivery deadline. Resolve relative dates "
            "using the supplied reference date. Do not invent missing quantities "
            "or deadlines. An exact catalog product name, quantity, and catalog "
            "sales unit are sufficient for a quote or inventory request. Do not "
            "ask for optional size, weight, color, or finish details when the "
            "customer requests an exact catalog item without those specifications. "
            "If essential information is missing or ambiguous, populate "
            "clarification_needed with a concise question. Do not treat reams or "
            "packs as individual sheets or units; ask for clarification when the "
            "conversion is unspecified. Interpret the request only; do not claim "
            "any action was completed. Preserve requested product specifications. "
            "Do not silently remove size, weight, color, or finish requirements "
            "to match a catalog product. For unsupported or ambiguous "
            "specifications, ask for clarification. Extract every requested item, "
            "including products that may be unsupported. Copy each item's product "
            "description from the customer message, preserving size, material, "
            "color, finish, and other specifications. Preserve the quantity and "
            "unit exactly as requested. Do not convert units, substitute products, "
            "or omit unfamiliar items. Catalog matching happens in a separate step."
        ),
    )

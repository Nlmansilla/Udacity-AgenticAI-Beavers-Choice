"""Construct the inventory Pydantic AI agent."""

from pydantic_ai import Agent

from ..tools.inventory import assess_inventory, list_available_inventory


def build_inventory_agent(model) -> Agent:
    """Build and return this worker agent."""
    return Agent(
        model=model,
        tools=[assess_inventory, list_available_inventory],
        instructions=(
            "Use the tools to answer stock-related queries. "
            "Check stock availability and replenishment needs. "
            "Never record purchases or sales. "
            "Describe supplier arrival dates as estimates conditional on placing "
            "a replenishment order; never imply an order has already been placed."
        ),
    )

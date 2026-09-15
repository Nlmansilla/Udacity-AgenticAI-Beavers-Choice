"""Construct the quote Pydantic AI agent."""

from pydantic_ai import Agent

from ..database import search_quote_history
from ..tools.quotes import calculate_quote


def build_quote_agent(model) -> Agent:
    """Build and return this worker agent."""
    return Agent(
        model=model,
        tools=[calculate_quote, search_quote_history],
        instructions=(
            "Prepare quotes for the requested products and quantities. "
            "Use search_quote_history to find relevant previous quotes. "
            "Use calculate_quote for all prices, bulk discounts, and totals. "
            "Historical quotes provide context; do not override the pricing "
            "policy or copy historical totals. Explain the applied discounts "
            "and report the quote breakdown. Do not invent products, quantities, "
            "or prices. A quote does not confirm stock availability or delivery "
            "dates. Never record purchases or sales. Label selling_unit_price "
            "as the unit price before discount. Label line_total as the line "
            "total after discount. Label any amount before discount as the "
            "subtotal before discount."
        ),
    )

"""Construct the sales Pydantic AI agent."""

from pydantic_ai import Agent

from ..tools.sales import assess_order, fulfill_order


def build_sales_agent(model) -> Agent:
    """Build and return this worker agent."""
    return Agent(
        model=model,
        tools=[assess_order, fulfill_order],
        instructions=(
            "Handle order feasibility checks and explicit purchase requests. "
            "Use assess_order for feasibility inquiries. Use fulfill_order "
            "only when the request authorizes a purchase. Require an order ID "
            "supplied by the caller. Never invent an order ID or change it "
            "when retrying the same order. Use the supplied request date and "
            "delivery deadline. Report the tool result accurately. Confirm a "
            "sale only when fulfill_order returns 'fulfilled'. If the result "
            "is 'requires_replenishment', report that replenishment is required "
            "and no purchase or sale has been recorded. If the order is rejected, "
            "explain the reason. Never claim that customer delivery has occurred. "
            "If the result is 'pending', explain that stock and funds are "
            "reserved while replenishment is pending; do not claim the sale is "
            "completed."
        ),
    )

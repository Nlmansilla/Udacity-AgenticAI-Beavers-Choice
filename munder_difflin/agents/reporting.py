"""Construct the reporting Pydantic AI agent."""

from pydantic_ai import Agent

from ..database import (generate_financial_report, get_all_inventory,
                        get_cash_balance)


def build_reporting_agent(model) -> Agent:
    """Build and return this worker agent."""
    return Agent(
        model=model,
        tools=[get_all_inventory, get_cash_balance, generate_financial_report],
        instructions=(
            "Answer questions about current inventory levels, cash balance, "
            "and overall financial standing using the tools provided. Use the "
            "request_date field of the input as the as_of_date argument for "
            "every tool call. Use generate_financial_report for a comprehensive "
            "report request. Use get_cash_balance for cash-only questions and "
            "get_all_inventory for a stock-only snapshot. Report tool results "
            "accurately without inventing figures. Never record purchases or sales."
        ),
    )

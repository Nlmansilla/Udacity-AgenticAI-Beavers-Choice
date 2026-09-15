"""Agent factories and the configured five-agent system."""

from dataclasses import dataclass

from pydantic_ai import Agent

from .inventory import build_inventory_agent
from .orchestrator import build_orchestrator_agent
from .quote import build_quote_agent
from .reporting import build_reporting_agent
from .sales import build_sales_agent


@dataclass(frozen=True)
class AgentSystem:
    """Hold the orchestrator and its four specialist agents."""

    model: object
    orchestrator_agent: Agent
    inventory_agent: Agent
    quote_agent: Agent
    sales_agent: Agent
    reporting_agent: Agent


def build_agent_system(model) -> AgentSystem:
    """Build all agents around one shared model configuration."""
    return AgentSystem(
        model=model,
        orchestrator_agent=build_orchestrator_agent(model),
        inventory_agent=build_inventory_agent(model),
        quote_agent=build_quote_agent(model),
        sales_agent=build_sales_agent(model),
        reporting_agent=build_reporting_agent(model),
    )


_DEFAULT_AGENT_SYSTEM = None


def get_default_agent_system() -> AgentSystem:
    """Lazily construct agents for compatibility helper calls."""
    global _DEFAULT_AGENT_SYSTEM
    if _DEFAULT_AGENT_SYSTEM is None:
        from ..config import create_model

        _DEFAULT_AGENT_SYSTEM = build_agent_system(create_model())
    return _DEFAULT_AGENT_SYSTEM

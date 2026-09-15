"""Command-line entry point for the evaluation run."""

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from .agents import build_agent_system
from .config import create_model
from .database import configure_database_engine
from .evaluation import run_test_scenarios


def main():
    """Initialize an isolated evaluation database and run all scenarios."""
    configure_database_engine(
        create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    )
    agent_system = build_agent_system(create_model())
    return run_test_scenarios(agent_system)

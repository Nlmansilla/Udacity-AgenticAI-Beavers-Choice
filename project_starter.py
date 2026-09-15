"""Compatibility entry point for the modular multi-agent application."""

from munder_difflin.agents import build_agent_system, get_default_agent_system
from munder_difflin.catalog import MARKUP_RATE, paper_supplies
from munder_difflin.catalog_matching import (CATALOG_MATCHING_INSTRUCTIONS,
                                             build_order_items,
                                             resolve_catalog_items,
                                             units_match,
                                             validate_match_coverage)
from munder_difflin.cli import main
from munder_difflin.database import (configure_database_engine,
                                     create_transaction,
                                     generate_financial_report,
                                     get_all_inventory, get_cash_balance,
                                     get_database_engine, get_reserved_cash,
                                     get_reserved_stock, get_stock_level,
                                     get_supplier_delivery_date,
                                     search_quote_history)
from munder_difflin.database_setup import (generate_sample_inventory,
                                           init_database)
from munder_difflin.dispatch import dispatch_request
from munder_difflin.evaluation import run_quote_test_cases, run_test_scenarios
from munder_difflin.schemas import (CatalogMatch, CustomerRequest,
                                    InventoryAssessment, OrderAssessment,
                                    OrderResult, ParsedCustomerRequest,
                                    QuoteAssessment, QuoteItemRequest,
                                    QuoteLine, RequestedItem, ReservationLine)
from munder_difflin.tools.inventory import (assess_inventory,
                                            list_available_inventory)
from munder_difflin.tools.order_utils import consolidate_items
from munder_difflin.tools.quotes import calculate_quote, get_bulk_discount
from munder_difflin.tools.sales import (assess_order, fulfill_order,
                                        process_pending_orders)

__all__ = [
    "MARKUP_RATE",
    "CATALOG_MATCHING_INSTRUCTIONS",
    "CatalogMatch",
    "CustomerRequest",
    "InventoryAssessment",
    "OrderAssessment",
    "OrderResult",
    "ParsedCustomerRequest",
    "QuoteAssessment",
    "QuoteItemRequest",
    "QuoteLine",
    "RequestedItem",
    "ReservationLine",
    "assess_inventory",
    "assess_order",
    "build_agent_system",
    "build_order_items",
    "calculate_quote",
    "consolidate_items",
    "configure_database_engine",
    "create_transaction",
    "dispatch_request",
    "fulfill_order",
    "generate_financial_report",
    "generate_sample_inventory",
    "get_all_inventory",
    "get_bulk_discount",
    "get_cash_balance",
    "get_database_engine",
    "get_reserved_cash",
    "get_reserved_stock",
    "get_stock_level",
    "get_supplier_delivery_date",
    "init_database",
    "list_available_inventory",
    "main",
    "paper_supplies",
    "process_pending_orders",
    "resolve_catalog_items",
    "run_quote_test_cases",
    "run_test_scenarios",
    "search_quote_history",
    "units_match",
    "validate_match_coverage",
]


def __getattr__(name):
    """Keep legacy access to the configured engine and agent instances."""
    if name == "db_engine":
        return get_database_engine()
    if name == "model" or name.endswith("_agent"):
        return getattr(get_default_agent_system(), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    main()

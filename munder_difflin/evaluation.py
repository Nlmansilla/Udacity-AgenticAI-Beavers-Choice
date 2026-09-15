"""Run the supplied purchase scenarios and supplemental quote cases."""

import json
import time
from datetime import date
from typing import Dict, List

import pandas as pd
from sqlalchemy.sql import text

from .agents import get_default_agent_system
from .catalog_matching import build_order_items, resolve_catalog_items
from .database import generate_financial_report, get_database_engine
from .database_setup import init_database
from .dispatch import dispatch_request
from .schemas import CustomerRequest, OrderResult
from .tools.quotes import calculate_quote
from .tools.sales import process_pending_orders


def run_quote_test_cases(
    request_date: str,
    cash_balance: float,
    inventory_value: float,
    agent_system=None,
) -> List[Dict]:
    """Evaluate three explicit quote requests without recording transactions."""
    if agent_system is None:
        agent_system = get_default_agent_system()

    quote_cases = [
        {
            "request_id": "quote-1",
            "request": "Could you send me a quote for 100 sheets of standard A4 paper?",
            "expected_items": [("A4 paper", 100)],
        },
        {
            "request_id": "quote-2",
            "request": "Please quote 600 sheets of standard cardstock.",
            "expected_items": [("Cardstock", 600)],
        },
        {
            "request_id": "quote-3",
            "request": "I'd like a price quote for 1,200 sheets of standard letter-sized paper.",
            "expected_items": [("Letter-sized paper", 1200)],
        },
    ]
    quote_results = []

    for case in quote_cases:
        print(f"\n=== Quote evaluation {case['request_id']} ===")
        request_with_date = (
            f"{case['request']} (Date of request: {request_date})"
        )
        parsed_result = agent_system.orchestrator_agent.run_sync(
            request_with_date)
        request = CustomerRequest(
            **parsed_result.output.model_dump(),
            request_date=date.fromisoformat(request_date),
            order_id=None,
        )

        catalog_matches = []
        quote_assessment = None
        failure_reason = None
        try:
            if request.intent != "quote":
                failure_reason = (
                    f"Expected quote intent, but parsed {request.intent!r}."
                )
                response = failure_reason
            elif request.clarification_needed:
                response = dispatch_request(
                    request, matches=catalog_matches, agent_system=agent_system
                )
                failure_reason = request.clarification_needed
            else:
                catalog_matches = resolve_catalog_items(
                    request.items, agent_system.orchestrator_agent)
                order_items = build_order_items(request.items, catalog_matches)
                quote_assessment = calculate_quote(order_items)
                actual_items = [
                    (line.item_name, line.quantity)
                    for line in quote_assessment.items
                ]
                if actual_items != case["expected_items"]:
                    failure_reason = (
                        f"Expected quote items {case['expected_items']!r}, "
                        f"but calculated {actual_items!r}."
                    )
                    quote_assessment = None
                    response = failure_reason
                else:
                    response = dispatch_request(
                        request, matches=catalog_matches, agent_system=agent_system
                    )
        except ValueError as error:
            failure_reason = f"Quote evaluation failed: {error}"
            response = failure_reason

        if not response and failure_reason is None:
            failure_reason = "The quote agent returned an empty response."

        is_quoted = (
            request.intent == "quote"
            and quote_assessment is not None
            and bool(response)
        )
        quote_results.append(
            {
                "request_id": case["request_id"],
                "order_id": None,
                "request_date": request_date,
                "original_request": case["request"],
                "parsed_request": request.model_dump_json(),
                "catalog_matches": json.dumps([
                    match.model_dump() for match in catalog_matches
                ]),
                "intent": request.intent,
                "cash_balance": cash_balance,
                "inventory_value": inventory_value,
                "response": response,
                "quote_assessment": (
                    quote_assessment.model_dump_json()
                    if quote_assessment is not None
                    else None
                ),
                "quote_total_amount": (
                    quote_assessment.total_amount
                    if quote_assessment is not None
                    else None
                ),
                "expected_quote_items": json.dumps(case["expected_items"]),
                "final_status": "quoted" if is_quoted else "quote_failed",
                "final_reason": (
                    "Quote calculated; no purchase or sale was recorded."
                    if is_quoted
                    else failure_reason or response
                ),
                "final_sale_amount": 0.0,
            }
        )
        print(f"Response: {response}")
        print(
            "Quote total: "
            f"${quote_assessment.total_amount:.2f}"
            if quote_assessment is not None
            else "Quote was not completed."
        )

    return quote_results


def run_test_scenarios(agent_system=None):
    """Run the supplied customer requests through the multi-agent system."""
    if agent_system is None:
        agent_system = get_default_agent_system()

    print("Initializing Database...")
    init_database(get_database_engine())
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values(
            "request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime(
        "%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx + 1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        # Process arrivals and complete pending orders before new requests.
        completed_orders = process_pending_orders(request_date)

        for completed_order in completed_orders:
            print(completed_order.model_dump_json(indent=2))

        # Refresh balances after processing pending orders.
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        parsed_result = agent_system.orchestrator_agent.run_sync(
            request_with_date)
        request = CustomerRequest(
            **parsed_result.output.model_dump(),
            request_date=date.fromisoformat(request_date),
            order_id=f"sample-{idx + 1}",
        )

        catalog_matches = []
        try:
            if not request.clarification_needed:
                catalog_matches = resolve_catalog_items(
                    request.items, agent_system.orchestrator_agent
                )
            response = dispatch_request(
                request, matches=catalog_matches, agent_system=agent_system
            )
        except ValueError as error:
            response = (
                f"Catalog resolution could not be validated: {error} "
                "No order has been placed."
            )

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "order_id": request.order_id,
                "request_date": request_date,
                "original_request": row["request"],
                "parsed_request": request.model_dump_json(),
                "catalog_matches": json.dumps([
                    match.model_dump() for match in catalog_matches
                ]),
                "intent": request.intent,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime(
        "%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Add quote-only evaluations after purchase scenarios to avoid changing them.
    results.extend(
        run_quote_test_cases(
            final_date,
            final_report["cash_balance"],
            final_report["inventory_value"],
            agent_system,
        )
    )

    # Read final order states before the in-memory database is discarded.
    with get_database_engine().connect() as connection:
        saved_orders = connection.execute(
            text("SELECT order_id, result_payload FROM orders")
        ).mappings().all()

    final_results = {
        row["order_id"]: OrderResult.model_validate_json(
            row["result_payload"]
        )
        for row in saved_orders
    }

    for entry in results:
        if entry["intent"] == "quote":
            continue

        final_result = final_results.get(entry["order_id"])

        if final_result is not None:
            entry["final_status"] = final_result.status
            entry["final_reason"] = final_result.reason
            entry["final_sale_amount"] = final_result.total_amount
        else:
            entry["final_status"] = "no_order_record"
            entry["final_reason"] = entry["response"]
            entry["final_sale_amount"] = 0.0

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results

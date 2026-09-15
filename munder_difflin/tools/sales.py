"""Order feasibility, fulfillment, reservations, and pending-order tools."""

import json
from datetime import date
from typing import List

from sqlalchemy.sql import text

from .. import database
from ..catalog import paper_supplies
from ..database import (create_transaction, get_cash_balance,
                        get_reserved_cash)
from ..schemas import (OrderAssessment, OrderResult, QuoteItemRequest,
                       ReservationLine)
from .inventory import assess_inventory
from .order_utils import consolidate_items
from .quotes import calculate_quote


def assess_order(
    items: List[QuoteItemRequest],
        request_date: str,
        delivery_due_date: str
) -> OrderAssessment:
    """Check delivery feasibility and replenishment funding for an order."""

    if not items:
        raise ValueError("At least one item is required.")

    items = consolidate_items(items)

    items_assessments = []
    for item in items:
        item_assessment = assess_inventory(
            item.item_name,
            item.quantity,
            request_date,
            delivery_due_date)
        items_assessments.append((item, item_assessment))

    cash_balance = get_cash_balance(request_date)
    reserved_cash = get_reserved_cash(request_date)
    available_cash = cash_balance - reserved_cash

    catalog = {
        product["item_name"]: product["unit_price"]
        for product in paper_supplies
    }

    replenishment_cost = 0.0

    deadline_failures = []
    # Calculate replenishment cost
    for item, assessment in items_assessments:
        if item.item_name not in catalog:
            raise ValueError(f"Unknown product: {item.item_name}")

        unit_cost = catalog[item.item_name]
        replenishment_cost += assessment.missing_quantity * unit_cost

        if not assessment.can_meet_deadline:
            deadline_failures.append(
                (item.item_name, assessment.supplier_delivery_date))

    replenishment_cost = round(replenishment_cost, 2)

    if deadline_failures:
        details = "; ".join(
            f"{name}: estimated supplier arrival {arrival}"
            if arrival is not None
            else f"{name}: deadline precedes the request date"
            for name, arrival in deadline_failures
        )

        return OrderAssessment(
            can_fulfill=False,
            reason=f"Cannot meet the deadline {delivery_due_date}. {details}",
            replenishment_cost=replenishment_cost,
            cash_balance=cash_balance,
        )

    # check balance
    if replenishment_cost > available_cash:
        return OrderAssessment(
            can_fulfill=False,
            reason=(
                f"Insufficient funds for replenishment. "
                f"Available: {available_cash:.2f}; "
                f"required: {replenishment_cost:.2f}."
            ),
            replenishment_cost=replenishment_cost,
            cash_balance=cash_balance,
        )

    return OrderAssessment(
        can_fulfill=True,
        reason=(
            "The order meets inventory availability and funding requirements. "
            "No purchases or sales have been recorded."
        ),
        replenishment_cost=replenishment_cost,
        cash_balance=cash_balance,
    )


def fulfill_order(
    order_id: str,
    items: List[QuoteItemRequest],
    request_date: str,
    delivery_due_date: str,
) -> OrderResult:
    """Fulfill an order from available stock after validating its feasibility."""
    if not order_id or not order_id.strip():
        raise ValueError("Order ID is required.")

    if not items:
        raise ValueError("At least one item is required.")

    items = consolidate_items(items)

    request_payload = json.dumps(
        {
            "items": [
                item.model_dump()
                for item in sorted(items, key=lambda item: item.item_name)
            ],
            "request_date": date.fromisoformat(request_date).isoformat(),
            "delivery_due_date": date.fromisoformat(delivery_due_date).isoformat(),
        },
        sort_keys=True,
    )

    with database.get_database_engine().connect() as connection:
        existing_order = connection.execute(
            text("""
                SELECT request_payload, result_payload
                FROM orders
                WHERE order_id = :order_id
            """),
            {"order_id": order_id},
        ).mappings().first()

    if existing_order is not None:
        if existing_order["request_payload"] != request_payload:
            raise ValueError(
                "Order ID already exists with different request data."
            )

        return OrderResult.model_validate_json(
            existing_order["result_payload"]
        )

    assessment = assess_order(items, request_date, delivery_due_date)

    if not assessment.can_fulfill:
        return OrderResult(
            status="rejected",
            reason=assessment.reason,
            total_amount=0.0
        )

    if assessment.replenishment_cost > 0:
        catalog = {
            product["item_name"]: product["unit_price"]
            for product in paper_supplies
        }
        reservations = []

        for item in items:
            inventory_assessment = assess_inventory(
                item.item_name,
                item.quantity,
                request_date,
                delivery_due_date,
            )

            reservations.append(
                ReservationLine(
                    item_name=item.item_name,
                    reserved_quantity=min(
                        item.quantity,
                        inventory_assessment.current_stock,
                    ),
                    incoming_quantity=inventory_assessment.missing_quantity,
                    reserved_cash=(
                        inventory_assessment.missing_quantity
                        * catalog[item.item_name]
                    ),
                    supplier_delivery_date=(
                        inventory_assessment.supplier_delivery_date
                    ),
                )
            )

        result = OrderResult(
            status="pending",
            reason=(
                "The order is pending replenishment. "
                "Available stock and replenishment funds have been reserved. "
                "No purchases or sales have been recorded."
            ),
            total_amount=0.0,
        )

        with database.get_database_engine().begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO orders (
                        order_id, request_payload, result_payload
                    )
                    VALUES (:order_id, :request_payload, :result_payload)
                """),
                {
                    "order_id": order_id,
                    "request_payload": request_payload,
                    "result_payload": result.model_dump_json(),
                },
            )

            for reservation in reservations:
                connection.execute(
                    text("""
                        INSERT INTO order_reservations (
                            order_id, item_name, reserved_quantity,
                            incoming_quantity, reserved_cash,
                            supplier_delivery_date, reserved_at, released_at
                        )
                        VALUES (
                            :order_id, :item_name, :reserved_quantity,
                            :incoming_quantity, :reserved_cash,
                            :supplier_delivery_date, :reserved_at, NULL
                        )
                    """),
                    {
                        **reservation.model_dump(mode="json"),
                        "order_id": order_id,
                        "reserved_at": date.fromisoformat(
                            request_date
                        ).isoformat(),
                    },
                )

        return result

    quote = calculate_quote(items)

    result = OrderResult(
        status="fulfilled",
        reason="The sale has been recorded using available stock.",
        total_amount=quote.total_amount,
    )

    with database.get_database_engine().begin() as connection:
        for line in quote.items:
            create_transaction(
                item_name=line.item_name,
                transaction_type="sales",
                quantity=line.quantity,
                price=line.line_total,
                date=request_date,
                connection=connection,
            )

        # Save one order record after recording all sale lines.
        connection.execute(
            text("""
                INSERT INTO orders (order_id, request_payload, result_payload)
                VALUES (:order_id, :request_payload, :result_payload)
            """),
            {
                "order_id": order_id,
                "request_payload": request_payload,
                "result_payload": result.model_dump_json(),
            },
        )

    return result


def process_pending_orders(as_of_date: str) -> List[OrderResult]:
    """Receive due replenishments and fulfill ready pending orders."""
    cutoff_date = date.fromisoformat(as_of_date).isoformat()
    completed_orders = []

    with database.get_database_engine().begin() as connection:
        due_reservations = connection.execute(
            text("""
                SELECT *
                FROM order_reservations
                WHERE incoming_quantity > 0
                  AND received_at IS NULL
                  AND released_at IS NULL
                  AND reserved_at <= :as_of_date
                  AND supplier_delivery_date <= :as_of_date
                ORDER BY supplier_delivery_date, order_id, item_name
            """),
            {"as_of_date": cutoff_date},
        ).mappings().all()

        for reservation in due_reservations:
            arrival_date = reservation["supplier_delivery_date"]

            create_transaction(
                item_name=reservation["item_name"],
                transaction_type="stock_orders",
                quantity=reservation["incoming_quantity"],
                price=reservation["reserved_cash"],
                date=arrival_date,
                connection=connection,
            )

            connection.execute(
                text("""
                    UPDATE order_reservations
                    SET received_at = :received_at
                    WHERE order_id = :order_id
                      AND item_name = :item_name
                """),
                {
                    "received_at": arrival_date,
                    "order_id": reservation["order_id"],
                    "item_name": reservation["item_name"],
                },
            )

        ready_orders = connection.execute(
            text("""
                SELECT
                    order_id,
                    MAX(
                        CASE
                            WHEN incoming_quantity > 0 THEN received_at
                            ELSE reserved_at
                        END
                    ) AS fulfillment_date
                FROM order_reservations
                WHERE released_at IS NULL
                  AND reserved_at <= :as_of_date
                GROUP BY order_id
                HAVING SUM(
                    CASE
                        WHEN incoming_quantity > 0
                             AND (
                                 received_at IS NULL
                                 OR received_at > :as_of_date
                             )
                        THEN 1
                        ELSE 0
                    END
                ) = 0
                ORDER BY fulfillment_date, order_id
            """),
            {"as_of_date": cutoff_date},
        ).mappings().all()

        for ready_order in ready_orders:
            order_id = ready_order["order_id"]
            fulfillment_date = ready_order["fulfillment_date"]

            saved_payload = connection.execute(
                text("""
                    SELECT request_payload
                    FROM orders
                    WHERE order_id = :order_id
                """),
                {"order_id": order_id},
            ).scalar_one()

            payload = json.loads(saved_payload)
            items = [
                QuoteItemRequest.model_validate(item)
                for item in payload["items"]
            ]
            quote = calculate_quote(items)

            for line in quote.items:
                create_transaction(
                    item_name=line.item_name,
                    transaction_type="sales",
                    quantity=line.quantity,
                    price=line.line_total,
                    date=fulfillment_date,
                    connection=connection,
                )

            result = OrderResult(
                status="fulfilled",
                reason=(
                    f"Order {order_id} was fulfilled on {fulfillment_date}. "
                    "Replenishments were received and the sale was recorded."
                ),
                total_amount=quote.total_amount,
            )

            connection.execute(
                text("""
                    UPDATE order_reservations
                    SET released_at = :released_at
                    WHERE order_id = :order_id
                      AND released_at IS NULL
                """),
                {
                    "released_at": fulfillment_date,
                    "order_id": order_id,
                },
            )

            connection.execute(
                text("""
                    UPDATE orders
                    SET result_payload = :result_payload
                    WHERE order_id = :order_id
                """),
                {
                    "result_payload": result.model_dump_json(),
                    "order_id": order_id,
                },
            )

            completed_orders.append(result)

    return completed_orders

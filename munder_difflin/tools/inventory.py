"""Inventory availability and supplier lead-time tools."""

from datetime import date
from typing import Dict

from ..database import (get_all_inventory, get_reserved_stock, get_stock_level,
                        get_supplier_delivery_date)
from ..schemas import InventoryAssessment


def assess_inventory(
    item_name: str,
    requested_quantity: int,
    request_date: str,
    delivery_due_date: str,
) -> InventoryAssessment:
    """
    Evaluates availability for a specific product at an specific due date

    Args:
    item_name: Product name. Must match the name in the inventory.
    requested_quantity: Requested amount. Must be an integer greater than zero.
    request_date: Request date in YYYY-MM-DD format.
    delivery_due_date: Due date in YYYY-MM-DD format.

    Returns:
    Returns:
    InventoryAssessment with the following fields:
        current_stock (int): Physical stock minus active reservations.
        missing_quantity (int): Additional units needed to fulfill the request.
        supplier_delivery_date (date | None): Estimated supplier arrival date,
            or None when no replenishment is needed.
        can_meet_deadline (bool): Whether inventory availability meets the
            deadline, excluding customer shipping and replenishment funding.
    """
    if requested_quantity <= 0:
        raise ValueError(
            f"Requested quantity must be greater than zero. "
            f"Received: {requested_quantity}"
        )
    stock = get_stock_level(item_name, request_date)
    physical_stock = int(stock["current_stock"].iloc[0])
    reserved_stock = get_reserved_stock(item_name, request_date)
    current_stock = physical_stock - reserved_stock

    if current_stock < 0:
        raise ValueError("Reserved stock exceeds physical stock.")

    missing_quantity = max(0, requested_quantity - current_stock)
    supplier_delivery_date = None

    available_date = date.fromisoformat(request_date)

    if missing_quantity > 0:
        supplier_delivery_date = get_supplier_delivery_date(
            request_date, missing_quantity)
        available_date = date.fromisoformat(supplier_delivery_date)

    can_meet_deadline = available_date <= date.fromisoformat(delivery_due_date)

    return InventoryAssessment(
        current_stock=current_stock,
        missing_quantity=missing_quantity,
        supplier_delivery_date=supplier_delivery_date,
        can_meet_deadline=can_meet_deadline
    )


def list_available_inventory(as_of_date: str) -> Dict[str, int]:
    """Return positive stock available after subtracting active reservations."""
    physical_inventory = get_all_inventory(as_of_date)
    available_inventory = {}

    for item_name, quantity in physical_inventory.items():
        reserved = get_reserved_stock(item_name, as_of_date)
        available = int(quantity) - reserved

        if available < 0:
            raise ValueError(
                f"Reserved stock exceeds physical stock for {item_name}."
            )

        if available > 0:
            available_inventory[item_name] = available

    return available_inventory

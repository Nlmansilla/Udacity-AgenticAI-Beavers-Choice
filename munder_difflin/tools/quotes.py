"""Deterministic quote calculation and quantity discount rules."""

from typing import List

from ..catalog import MARKUP_RATE, paper_supplies
from ..schemas import QuoteAssessment, QuoteItemRequest, QuoteLine
from .order_utils import consolidate_items


def calculate_quote(items: List[QuoteItemRequest]) -> QuoteAssessment:
    """Calculate a quote using a 25% markup on acquisition costs."""
    catalog = {
        product["item_name"]: product["unit_price"]
        for product in paper_supplies
    }

    if not items:
        raise ValueError("At least one item is required.")

    quote_lines = []

    items = consolidate_items(items)

    for item in items:
        if item.item_name not in catalog:
            raise ValueError(f"Unknown product: {item.item_name}")
        unit_cost = catalog[item.item_name]
        selling_unit_price = float(unit_cost + unit_cost * MARKUP_RATE)
        discount_rate = get_bulk_discount(item.quantity)
        line_total = round(
            item.quantity * selling_unit_price * (1 - discount_rate), 2)
        quote_line = QuoteLine(
            item_name=item.item_name,
            quantity=item.quantity,
            selling_unit_price=selling_unit_price,
            line_total=line_total,
            discount_rate=discount_rate
        )
        quote_lines.append(quote_line)

    return QuoteAssessment(
        items=quote_lines,
        total_amount=round(
            sum(line.line_total for line in quote_lines), 2
        )
    )


def get_bulk_discount(quantity: int) -> float:
    """Return the discount rate based on the quantity of one product"""
    if quantity >= 1000:
        return 0.10
    if quantity >= 500:
        return 0.05
    return 0

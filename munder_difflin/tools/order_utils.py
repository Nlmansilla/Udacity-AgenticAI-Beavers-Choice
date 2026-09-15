"""Shared order-line normalization helpers."""

from collections import Counter
from typing import List

from ..schemas import QuoteItemRequest


def consolidate_items(
    items: List[QuoteItemRequest]
) -> List[QuoteItemRequest]:
    """Combine quantities for repeated product names."""
    quantities = Counter()

    for item in items:
        quantities[item.item_name] += item.quantity

    return [
        QuoteItemRequest(item_name=name, quantity=quantity)
        for name, quantity in quantities.items()
    ]

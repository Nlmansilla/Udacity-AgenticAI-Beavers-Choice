"""Pydantic input and result schemas shared by tools and agents."""

from datetime import date
from typing import List, Literal

from pydantic import BaseModel, Field


class InventoryAssessment(BaseModel):
    """Summarize available inventory and whether its delivery meets a deadline."""

    current_stock: int = Field(ge=0)
    missing_quantity: int = Field(ge=0)
    supplier_delivery_date: date | None = None
    can_meet_deadline: bool


class CatalogMatch(BaseModel):
    """Represent the catalog resolution for one requested product."""

    source_index: int = Field(ge=0)
    catalog_item_name: str | None = None
    status: Literal["matched", "needs_clarification", "unsupported"]
    reason: str


class QuoteItemRequest(BaseModel):
    """Represent a catalog item and its requested quantity."""

    item_name: str
    quantity: int = Field(gt=0)


class RequestedItem(BaseModel):
    """Preserve the customer's product description, amount, and unit."""

    original_description: str
    quantity: int = Field(gt=0)
    unit: str


class QuoteLine(BaseModel):
    """Represent one priced line in a quote."""

    item_name: str
    quantity: int
    selling_unit_price: float
    line_total: float
    discount_rate: float


class QuoteAssessment(BaseModel):
    """Represent the priced items and total for a quote."""

    items: List[QuoteLine]
    total_amount: float


class OrderAssessment(BaseModel):
    """Report whether an order is feasible and its funding requirements."""

    can_fulfill: bool
    reason: str
    replenishment_cost: float = Field(ge=0)
    cash_balance: float


class OrderResult(BaseModel):
    """Represent the final status and amount of an order."""

    status: Literal["fulfilled", "pending",
                    "rejected", "requires_replenishment"]
    reason: str
    total_amount: float = Field(ge=0)


class ReservationLine(BaseModel):
    """Describe inventory and cash reserved for one order line."""

    item_name: str
    reserved_quantity: int = Field(ge=0)
    incoming_quantity: int = Field(ge=0)
    reserved_cash: float = Field(ge=0)
    supplier_delivery_date: date | None = None


class ParsedCustomerRequest(BaseModel):
    """Represent an interpreted customer request before adding runtime fields."""

    intent: Literal["inventory", "quote", "purchase", "report"]
    items: List[RequestedItem] = Field(default_factory=list)
    delivery_due_date: date | None = None
    clarification_needed: str | None = None


class CustomerRequest(ParsedCustomerRequest):
    """Add request date and order identifier to an interpreted request."""

    request_date: date
    order_id: str | None = None

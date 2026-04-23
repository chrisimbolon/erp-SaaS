"""
modules/sales/domain/policies.py
==================================
All Sales business rules as pure functions.
No DB. No HTTP. Testable with zero mocks.

Following hr-app pattern (attendance/domain/policies.py).
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple

from app.modules.sales.domain.entities import (Invoice, SalesOrder,
                                               SalesOrderItem,
                                               SalesOrderStatus)


class SalesOrderPolicy:

    @staticmethod
    def can_confirm(order: SalesOrder) -> Tuple[bool, str]:
        if order.status != SalesOrderStatus.DRAFT:
            return False, f"Only DRAFT orders can be confirmed. Current: {order.status}"
        if not order.items:
            return False, "Cannot confirm an order with no items."
        for item in order.items:
            if item.quantity <= 0:
                return False, f"Item '{item.product_name}' has invalid quantity {item.quantity}."
            if item.unit_price <= 0:
                return False, f"Item '{item.product_name}' has invalid price {item.unit_price}."
        return True, ""

    @staticmethod
    def can_fulfill(order: SalesOrder) -> Tuple[bool, str]:
        if order.status != SalesOrderStatus.CONFIRMED:
            return False, f"Only CONFIRMED orders can be fulfilled. Current: {order.status}"
        return True, ""

    @staticmethod
    def can_cancel(order: SalesOrder) -> Tuple[bool, str]:
        if order.status == SalesOrderStatus.FULFILLED:
            return False, "Cannot cancel fulfilled order. Create a return instead."
        if order.status == SalesOrderStatus.CANCELLED:
            return False, "Order is already cancelled."
        return True, ""

    @staticmethod
    def validate_stock_availability(
        items: List[SalesOrderItem],
        available_stock: dict[int, Decimal],  # product_id → current available stock
    ) -> List[dict]:
        """
        Check all items against available stock.
        Returns list of shortage dicts (empty = all good).

        available_stock should subtract existing reservations:
            available = current_stock - reserved_quantity

        Returns:
            [
                {
                    "product_id": 101,
                    "product_name": "Pupuk NPK",
                    "requested": Decimal("50"),
                    "available": Decimal("30"),
                    "shortage": Decimal("20"),
                }
            ]
        """
        shortages = []
        for item in items:
            avail = available_stock.get(item.product_id, Decimal("0"))
            if item.quantity > avail:
                shortages.append({
                    "product_id":   item.product_id,
                    "product_name": item.product_name,
                    "requested":    item.quantity,
                    "available":    avail,
                    "shortage":     item.quantity - avail,
                })
        return shortages


class InvoicePolicy:

    DEFAULT_PAYMENT_TERMS_DAYS = 30   # NET 30 by default

    @staticmethod
    def calculate_due_date(
        issue_date: datetime,
        payment_terms_days: int = 30,
    ) -> datetime:
        return issue_date + timedelta(days=payment_terms_days)

    @staticmethod
    def can_record_payment(invoice: Invoice, amount: Decimal) -> Tuple[bool, str]:
        if invoice.status == Invoice.status.__class__.PAID:
            return False, "Invoice is already fully paid."
        if invoice.status == Invoice.status.__class__.CANCELLED:
            return False, "Cannot record payment for a cancelled invoice."
        if amount <= 0:
            return False, f"Payment amount must be positive. Got {amount}."
        if amount > invoice.total_amount:
            return False, (
                f"Payment {amount} exceeds invoice total {invoice.total_amount}. "
                f"Use exact amount or create credit note for overpayment."
            )
        return True, ""

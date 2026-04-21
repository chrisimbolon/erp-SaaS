"""
modules/purchase/domain/policies.py
=====================================
Business rules for the Purchase domain.
These are pure functions — no DB, no HTTP, no side effects.
Easy to unit test in isolation.

Following hr-app pattern (attendance/domain/policies.py).
"""

from decimal import Decimal

from .entities import GoodsReceiptItem, POStatus, PurchaseOrder


class PurchaseOrderPolicy:

    @staticmethod
    def can_receive_goods(po: PurchaseOrder) -> bool:
        """
        Goods can only be received against a CONFIRMED or PARTIALLY_RECEIVED PO.
        A DRAFT, CANCELLED, or FULLY_RECEIVED PO cannot accept more goods.
        """
        return po.status in (POStatus.CONFIRMED, POStatus.PARTIALLY_RECEIVED)

    @staticmethod
    def validate_receipt_quantities(
        po: PurchaseOrder,
        receipt_items: list[GoodsReceiptItem],
        already_received: dict[int, Decimal]  # product_id → qty already received
    ) -> list[str]:
        """
        Validate that receipt quantities don't exceed what was ordered.
        Returns a list of error messages (empty = valid).

        already_received: total qty received in PREVIOUS receipts for this PO.
        """
        errors = []
        ordered = {item.product_id: item.quantity_ordered for item in po.items}

        for receipt_item in receipt_items:
            pid = receipt_item.product_id
            if pid not in ordered:
                errors.append(f"Product {pid} is not in this Purchase Order")
                continue

            total_after = already_received.get(pid, Decimal(0)) + receipt_item.quantity_received
            if total_after > ordered[pid]:
                errors.append(
                    f"Product {pid}: receiving {receipt_item.quantity_received} would exceed "
                    f"ordered quantity of {ordered[pid]} (already received: {already_received.get(pid, 0)})"
                )

        return errors

    @staticmethod
    def can_cancel(po: PurchaseOrder) -> tuple[bool, str]:
        """
        Returns (can_cancel: bool, reason: str).
        """
        if po.status == POStatus.FULLY_RECEIVED:
            return False, "Cannot cancel a fully received Purchase Order"
        if po.status == POStatus.PARTIALLY_RECEIVED:
            return False, "Cannot cancel a partially received Purchase Order — create a return instead"
        if po.status == POStatus.CANCELLED:
            return False, "Purchase Order is already cancelled"
        return True, ""

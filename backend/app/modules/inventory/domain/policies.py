"""
modules/inventory/domain/policies.py
"""
from decimal import Decimal


class InventoryPolicy:

    @staticmethod
    def validate_positive_quantity(quantity: Decimal) -> None:
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")

    @staticmethod
    def can_fulfill_quantity(
        current_stock: Decimal,
        requested: Decimal
    ) -> tuple[bool, str]:
        """
        Stock cannot go below zero.
        Returns (can_fulfill, reason).
        """
        if requested > current_stock:
            return False, f"Requested {requested} but only {current_stock} available"
        return True, ""

    @staticmethod
    def is_low_stock(current: Decimal, minimum: Decimal) -> bool:
        return current <= minimum

"""
modules/inventory/domain/entities.py
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class MovementType(str, Enum):
    IN = "in"           # Stock arriving (purchase receipt, return from customer)
    OUT = "out"         # Stock leaving (sales fulfillment, return to supplier)
    ADJUSTMENT = "adjustment"  # Manual correction


@dataclass
class Product:
    id: Optional[int]
    tenant_id: int
    sku: str
    name: str
    unit: str           # kg, pcs, liter, etc.
    current_stock: Decimal
    minimum_stock: Decimal  # triggers "Stok Rendah" alert on dashboard
    cost_price: Decimal     # average cost
    sell_price: Decimal
    category_id: Optional[int] = None
    is_active: bool = True

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.minimum_stock

    @property
    def stock_value(self) -> Decimal:
        """Current inventory value at cost price."""
        return self.current_stock * self.cost_price


@dataclass
class StockMovement:
    id: Optional[int]
    tenant_id: int
    product_id: int
    movement_type: MovementType
    quantity: Decimal
    stock_before: Decimal
    stock_after: Decimal
    reference_type: str     # "goods_receipt", "sales_order", "manual_adjustment"
    reference_id: int
    reference_number: str
    movement_date: datetime
    notes: Optional[str] = None

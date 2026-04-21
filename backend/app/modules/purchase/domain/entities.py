"""
modules/purchase/domain/entities.py
====================================
Pure Python domain entities. NO SQLAlchemy here.
These are the business objects — they carry behaviour, not just data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class POStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PARTIALLY_RECEIVED = "partially_received"
    FULLY_RECEIVED = "fully_received"
    CANCELLED = "cancelled"


class GoodsReceiptStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass
class PurchaseOrderItem:
    product_id: int
    product_name: str
    quantity_ordered: Decimal
    unit_price: Decimal
    unit: str  # e.g. "kg", "pcs", "liter"

    @property
    def subtotal(self) -> Decimal:
        return self.quantity_ordered * self.unit_price


@dataclass
class PurchaseOrder:
    id: Optional[int]
    tenant_id: int
    supplier_id: int
    po_number: str
    status: POStatus
    items: List[PurchaseOrderItem]
    order_date: datetime
    expected_delivery: Optional[datetime] = None
    notes: Optional[str] = None

    @property
    def total_amount(self) -> Decimal:
        return sum(item.subtotal for item in self.items)

    def confirm(self) -> None:
        """Business rule: only DRAFT can be confirmed."""
        if self.status != POStatus.DRAFT:
            raise ValueError(f"Cannot confirm PO in status '{self.status}'")
        self.status = POStatus.CONFIRMED

    def cancel(self) -> None:
        """Business rule: cannot cancel once receiving has started."""
        if self.status in (POStatus.PARTIALLY_RECEIVED, POStatus.FULLY_RECEIVED):
            raise ValueError("Cannot cancel PO that has already been (partially) received")
        self.status = POStatus.CANCELLED


@dataclass
class GoodsReceiptItem:
    product_id: int
    quantity_received: Decimal
    purchase_order_item_id: int


@dataclass
class GoodsReceipt:
    id: Optional[int]
    tenant_id: int
    purchase_order_id: int
    receipt_number: str
    items: List[GoodsReceiptItem]
    received_date: datetime
    received_by: int  # user_id
    notes: Optional[str] = None
    status: GoodsReceiptStatus = GoodsReceiptStatus.PENDING

    def complete(self) -> None:
        self.status = GoodsReceiptStatus.COMPLETED

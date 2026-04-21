"""
modules/purchase/domain/events.py
===================================
Domain events raised by the Purchase bounded context.

These are plain dataclasses — no framework dependency.
They describe WHAT HAPPENED in business language.

The EventBus carries these to other modules.
Inventory listens to GoodsReceivedEvent to update stock.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List


@dataclass
class ReceivedItem:
    """A single product line within a goods receipt event."""
    product_id: int
    quantity_received: Decimal
    unit: str


@dataclass
class GoodsReceivedEvent:
    """
    Fired when: GoodsReceipt is marked COMPLETED.
    Listened by: Inventory → stock_in use case

    This is the PRIMARY event that drives stock IN.
    """
    tenant_id: int
    purchase_order_id: int
    goods_receipt_id: int
    receipt_number: str
    supplier_id: int
    items: List[ReceivedItem]
    received_at: datetime
    received_by: int  # user_id

    def to_dict(self) -> Dict[str, Any]:
        """Serialise for EventBus.publish()"""
        return {
            "tenant_id": self.tenant_id,
            "purchase_order_id": self.purchase_order_id,
            "goods_receipt_id": self.goods_receipt_id,
            "receipt_number": self.receipt_number,
            "supplier_id": self.supplier_id,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity_received": str(item.quantity_received),
                    "unit": item.unit,
                }
                for item in self.items
            ],
            "received_at": self.received_at.isoformat(),
            "received_by": self.received_by,
        }


@dataclass
class PurchaseOrderCancelledEvent:
    """
    Fired when: A confirmed PO is cancelled.
    Listened by: Inventory (if any stock was pre-reserved)
    """
    tenant_id: int
    purchase_order_id: int
    po_number: str
    cancelled_by: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "purchase_order_id": self.purchase_order_id,
            "po_number": self.po_number,
            "cancelled_by": self.cancelled_by,
        }

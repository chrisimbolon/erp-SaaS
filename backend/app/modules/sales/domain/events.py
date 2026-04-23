"""
modules/sales/domain/events.py
================================
All domain events fired by the Sales bounded context.

Who listens:
  StockReservedEvent              → Inventory: reserve_stock handler
  OrderFulfilledEvent             → Inventory: handle_order_fulfilled_event (stock OUT)
  StockReservationReleasedEvent   → Inventory: release_reservation handler
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List


@dataclass
class ReservedItem:
    product_id: int
    quantity:   Decimal
    unit:       str


@dataclass
class StockReservedEvent:
    """
    Fired when: SalesOrder is CONFIRMED.
    Listened by: Inventory → reserve_stock handler

    Creates a soft reservation so the same stock
    can't be sold to another customer before delivery.
    """
    tenant_id:       int
    sales_order_id:  int
    order_number:    str
    customer_id:     int
    items:           List[ReservedItem]
    reserved_at:     datetime
    reserved_by:     int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id":      self.tenant_id,
            "sales_order_id": self.sales_order_id,
            "order_number":   self.order_number,
            "customer_id":    self.customer_id,
            "items": [
                {"product_id": i.product_id, "quantity": str(i.quantity), "unit": i.unit}
                for i in self.items
            ],
            "reserved_at": self.reserved_at.isoformat(),
            "reserved_by": self.reserved_by,
        }


@dataclass
class FulfilledItem:
    product_id:  int
    quantity:    Decimal
    unit:        str
    unit_price:  Decimal


@dataclass
class OrderFulfilledEvent:
    """
    Fired when: Surat Jalan is ISSUED (goods physically leave warehouse).
    Listened by: Inventory → handle_order_fulfilled_event
                 → stock OUT + release reservation in one operation
    """
    tenant_id:       int
    sales_order_id:  int
    surat_jalan_id:  int
    order_number:    str
    sj_number:       str
    customer_id:     int
    items:           List[FulfilledItem]
    fulfilled_at:    datetime
    fulfilled_by:    int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id":       self.tenant_id,
            "sales_order_id":  self.sales_order_id,
            "surat_jalan_id":  self.surat_jalan_id,
            "order_number":    self.order_number,
            "sj_number":       self.sj_number,
            "customer_id":     self.customer_id,
            "items": [
                {
                    "product_id": i.product_id,
                    "quantity":   str(i.quantity),
                    "unit":       i.unit,
                    "unit_price": str(i.unit_price),
                }
                for i in self.items
            ],
            "fulfilled_at": self.fulfilled_at.isoformat(),
            "fulfilled_by":  self.fulfilled_by,
        }


@dataclass
class StockReservationReleasedEvent:
    """
    Fired when: A CONFIRMED SalesOrder is CANCELLED.
    Listened by: Inventory → release_reservation handler

    Releases reserved qty back to available.
    NOT fired when order is FULFILLED — stock is already deducted.
    """
    tenant_id:       int
    sales_order_id:  int
    order_number:    str
    items:           List[ReservedItem]
    released_at:     datetime
    released_by:     int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id":      self.tenant_id,
            "sales_order_id": self.sales_order_id,
            "order_number":   self.order_number,
            "items": [
                {"product_id": i.product_id, "quantity": str(i.quantity), "unit": i.unit}
                for i in self.items
            ],
            "released_at": self.released_at.isoformat(),
            "released_by":  self.released_by,
        }

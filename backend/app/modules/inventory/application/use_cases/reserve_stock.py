"""
modules/inventory/application/use_cases/reserve_stock.py
==========================================================
Handles stock RESERVATION when a SalesOrder is CONFIRMED.

Reservation = soft lock. The stock hasn't physically left,
but it's committed to this order. No other order can use it.

DB model: StockReservation table
  - product_id, tenant_id, sales_order_id, quantity_reserved, is_active

Available stock for new orders = current_stock - SUM(active reservations)

This is also what validate_stock_availability() queries when
checking if a new order can be confirmed.

EventBus wiring (registered in main.py):
  EventBus.subscribe(Events.STOCK_RESERVED, handle_stock_reserved_event)
"""

from datetime import datetime
from decimal import Decimal

from app.core.database import SessionLocal
from app.modules.inventory.infrastructure.repository import InventoryRepository
from sqlalchemy.orm import Session


class ReserveStockUseCase:
    """
    Creates a StockReservation row for each item in the sales order.
    Called by EventBus when Sales fires StockReservedEvent.
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = InventoryRepository(db, tenant_id)

    def execute(
        self,
        sales_order_id: int,
        order_number: str,
        product_id: int,
        quantity: Decimal,
    ) -> None:
        """
        Reserve qty for a single product line.
        Called once per item in the sales order.
        """
        # Validate product exists for this tenant
        product = self.repo.get_product(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found for tenant {self.tenant_id}")

        # Check available stock (current - already reserved)
        available = self.repo.get_available_stock(product_id)
        if quantity > available:
            raise ValueError(
                f"Insufficient stock for product '{product.name}' (id={product_id}). "
                f"Requested: {quantity}, Available: {available}"
            )

        self.repo.create_reservation(
            product_id=product_id,
            sales_order_id=sales_order_id,
            order_number=order_number,
            quantity=quantity,
        )


# ─── EventBus Handler ─────────────────────────────────────────────────────────

def handle_stock_reserved_event(payload: dict) -> None:
    """
    Registered in main.py:
      EventBus.subscribe(Events.STOCK_RESERVED, handle_stock_reserved_event)

    Called when Sales fires StockReservedEvent (SO confirmed).
    Creates one reservation row per item.
    """
    db: Session = payload.get("_db")
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        use_case = ReserveStockUseCase(db=db, tenant_id=payload["tenant_id"])
        for item in payload["items"]:
            use_case.execute(
                sales_order_id=payload["sales_order_id"],
                order_number=payload["order_number"],
                product_id=item["product_id"],
                quantity=Decimal(item["quantity"]),
            )
    finally:
        if should_close:
            db.close()

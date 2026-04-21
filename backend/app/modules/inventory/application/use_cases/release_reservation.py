"""
modules/inventory/application/use_cases/release_reservation.py
================================================================
Releases stock reservation when a SalesOrder is CANCELLED.

Only called when a CONFIRMED order is cancelled.
FULFILLED orders don't need this — stock was already deducted.

EventBus wiring (registered in main.py):
  EventBus.subscribe(Events.STOCK_RESERVATION_RELEASED, handle_release_reservation_event)
"""

from decimal import Decimal

from app.core.database import SessionLocal
from app.modules.inventory.infrastructure.repository import InventoryRepository
from sqlalchemy.orm import Session


class ReleaseReservationUseCase:

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = InventoryRepository(db, tenant_id)

    def execute(self, sales_order_id: int) -> None:
        """
        Deactivate all active reservations for this sales order.
        Stock becomes available for other orders again.
        """
        self.repo.release_reservations(sales_order_id)


# ─── EventBus Handler ─────────────────────────────────────────────────────────

def handle_release_reservation_event(payload: dict) -> None:
    """
    Registered in main.py:
      EventBus.subscribe(Events.STOCK_RESERVATION_RELEASED, handle_release_reservation_event)
    """
    db: Session = payload.get("_db")
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        use_case = ReleaseReservationUseCase(db=db, tenant_id=payload["tenant_id"])
        use_case.execute(sales_order_id=payload["sales_order_id"])
    finally:
        if should_close:
            db.close()

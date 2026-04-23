"""
modules/sales/application/use_cases/cancel_sales_order.py
===========================================================
Cancels a SalesOrder.

Critical logic:
  - DRAFT     → cancel freely, no inventory interaction
  - CONFIRMED → cancel + fire StockReservationReleasedEvent
                → Inventory releases the soft reservation
  - FULFILLED → BLOCKED. Create retur penjualan instead.
"""

from datetime import datetime

from app.modules.sales.application.schemas import SalesOrderResponse
from app.modules.sales.domain.entities import SalesOrderStatus
from app.modules.sales.domain.events import (ReservedItem,
                                             StockReservationReleasedEvent)
from app.modules.sales.domain.policies import SalesOrderPolicy
from app.modules.sales.infrastructure.repository import SalesRepository
from app.shared.events.bus import EventBus, Events
from sqlalchemy.orm import Session


class CancelSalesOrderUseCase:

    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = SalesRepository(db, tenant_id)

    def execute(self, sales_order_id: int, reason: str = None) -> SalesOrderResponse:

        # ── Load order ────────────────────────────────────────────────────────
        order = self.repo.get_sales_order(sales_order_id)
        if not order:
            raise ValueError(f"SalesOrder {sales_order_id} not found")

        # ── Policy check ──────────────────────────────────────────────────────
        can, reason_msg = SalesOrderPolicy.can_cancel(order)
        if not can:
            raise ValueError(reason_msg)

        was_confirmed = order.status == SalesOrderStatus.CONFIRMED

        # ── Cancel ────────────────────────────────────────────────────────────
        order.cancel()
        self.repo.update_order_status(order.id, order.status)

        # ── Release reservation if it was CONFIRMED ───────────────────────────
        if was_confirmed:
            event = StockReservationReleasedEvent(
                tenant_id=self.tenant_id,
                sales_order_id=order.id,
                order_number=order.order_number,
                items=[
                    ReservedItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit=item.unit,
                    )
                    for item in order.items
                ],
                released_at=datetime.utcnow(),
                released_by=self.user_id,
            )
            EventBus.publish(
                Events.STOCK_RESERVATION_RELEASED,
                {**event.to_dict(), "_db": self.db}
            )

        return SalesOrderResponse.model_validate(order)

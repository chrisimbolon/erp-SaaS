"""
modules/sales/application/use_cases/confirm_sales_order.py
============================================================
Confirms a SalesOrder:
  1. Load order + validate via SalesOrderPolicy
  2. Check available stock for ALL items upfront
     → if ANY item is short: BLOCK with detailed shortage list
  3. order.confirm() → status = CONFIRMED
  4. Persist status change
  5. Fire StockReservedEvent → Inventory creates reservations

This is the "reserve on confirm" half of the reserve/deduct split.
The "deduct on Surat Jalan" half is in issue_surat_jalan.py.
"""

from datetime import datetime

from app.modules.inventory.infrastructure.repository import InventoryRepository
from app.modules.sales.application.schemas import SalesOrderResponse
from app.modules.sales.domain.events import ReservedItem, StockReservedEvent
from app.modules.sales.domain.policies import SalesOrderPolicy
from app.modules.sales.infrastructure.repository import SalesRepository
from app.shared.events.bus import EventBus, Events
from sqlalchemy.orm import Session


class ConfirmSalesOrderUseCase:
    """
    Confirms a draft sales order.
    Checks ALL stock shortages upfront and returns them in one shot
    so the user sees every problem, not just the first one.
    """

    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.sales_repo = SalesRepository(db, tenant_id)
        self.inv_repo = InventoryRepository(db, tenant_id)

    def execute(self, sales_order_id: int) -> SalesOrderResponse:

        # ── Step 1: Load order ────────────────────────────────────────────────
        order = self.sales_repo.get_sales_order(sales_order_id)
        if not order:
            raise ValueError(f"SalesOrder {sales_order_id} not found")

        # ── Step 2: Policy — can we confirm? ──────────────────────────────────
        can, reason = SalesOrderPolicy.can_confirm(order)
        if not can:
            raise ValueError(reason)

        # ── Step 3: Stock availability check — ALL items at once ──────────────
        product_ids = [item.product_id for item in order.items]
        available_stock = self.inv_repo.get_available_stock_bulk(product_ids)

        shortages = SalesOrderPolicy.validate_stock_availability(
            items=order.items,
            available_stock=available_stock,
        )

        if shortages:
            # Return ALL shortages so user can fix everything in one go
            shortage_lines = [
                f"  • {s['product_name']} (id={s['product_id']}): "
                f"need {s['requested']}, available {s['available']}, short by {s['shortage']}"
                for s in shortages
            ]
            raise ValueError(
                f"Cannot confirm order — insufficient stock for {len(shortages)} item(s):\n"
                + "\n".join(shortage_lines)
            )

        # ── Step 4: Confirm the order ─────────────────────────────────────────
        order.confirm()
        self.sales_repo.update_order_status(order.id, order.status)

        # ── Step 5: Fire StockReservedEvent → Inventory reserves stock ────────
        event = StockReservedEvent(
            tenant_id=self.tenant_id,
            sales_order_id=order.id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            items=[
                ReservedItem(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit=item.unit,
                )
                for item in order.items
            ],
            reserved_at=datetime.utcnow(),
            reserved_by=self.user_id,
        )

        EventBus.publish(Events.STOCK_RESERVED, {**event.to_dict(), "_db": self.db})

        return SalesOrderResponse.model_validate(order)

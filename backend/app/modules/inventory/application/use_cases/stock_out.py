"""
modules/inventory/application/use_cases/stock_out.py
======================================================
Handles stock OUT when Surat Jalan is ISSUED.

Two operations in one atomic step:
  1. Deduct quantity from product.current_stock
  2. Release the active reservation for this sales order

This is correct because:
  - On SO confirm → reservation was created (stock was soft-locked)
  - On SJ issue   → goods physically leave → deduct real stock
                   → reservation is no longer needed → release it
  - Net effect    → current_stock goes down, reservation cleared

If deduct_and_release fails (stock went negative somehow),
the whole transaction rolls back — no partial state.

EventBus wiring (registered in main.py):
  EventBus.subscribe(Events.ORDER_FULFILLED, handle_order_fulfilled_event)
"""

from datetime import datetime
from decimal import Decimal

from app.core.database import SessionLocal
from app.modules.inventory.domain.entities import MovementType, StockMovement
from app.modules.inventory.domain.policies import InventoryPolicy
from app.modules.inventory.infrastructure.repository import InventoryRepository
from sqlalchemy.orm import Session


class StockOutUseCase:

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = InventoryRepository(db, tenant_id)

    def execute(
        self,
        product_id: int,
        sales_order_id: int,
        quantity: Decimal,
        reference_type: str,
        reference_id: int,
        reference_number: str,
        notes: str = None,
    ) -> StockMovement:

        # ── Step 1: Validate ──────────────────────────────────────────────────
        product = self.repo.get_product(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found for tenant {self.tenant_id}")

        InventoryPolicy.validate_positive_quantity(quantity)

        # ── Step 2: Deduct stock + release reservation (atomic) ───────────────
        #
        # We use current_stock here (not available_stock) because:
        # The reservation was already counted when SO was confirmed.
        # Now we're doing the actual physical deduction.
        #
        stock_before, stock_after = self.repo.deduct_and_release(
            product_id=product_id,
            sales_order_id=sales_order_id,
            quantity=quantity,
        )

        # ── Step 3: Write immutable movement record ───────────────────────────
        movement = StockMovement(
            id=None,
            tenant_id=self.tenant_id,
            product_id=product_id,
            movement_type=MovementType.OUT,
            quantity=quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_number=reference_number,
            notes=notes,
            movement_date=datetime.utcnow(),
        )

        return self.repo.save_movement(movement)


# ─── EventBus Handler ─────────────────────────────────────────────────────────

def handle_order_fulfilled_event(payload: dict) -> None:
    """
    Registered in main.py:
      EventBus.subscribe(Events.ORDER_FULFILLED, handle_order_fulfilled_event)

    Called when Sales fires OrderFulfilledEvent (Surat Jalan issued).
    Deducts stock + releases reservation for each product line.
    Runs in the SAME db transaction as the Surat Jalan creation.
    """
    db: Session = payload.get("_db")
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        use_case = StockOutUseCase(db=db, tenant_id=payload["tenant_id"])

        for item in payload["items"]:
            use_case.execute(
                product_id=item["product_id"],
                sales_order_id=payload["sales_order_id"],
                quantity=Decimal(item["quantity"]),
                reference_type="surat_jalan",
                reference_id=payload["surat_jalan_id"],
                reference_number=payload["sj_number"],
                notes=f"Auto: Surat Jalan {payload['sj_number']} — SO #{payload['order_number']}",
            )

    finally:
        if should_close:
            db.close()

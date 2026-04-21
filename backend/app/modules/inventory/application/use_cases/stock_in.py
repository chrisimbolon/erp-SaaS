"""
modules/inventory/application/use_cases/stock_in.py
=====================================================
The Inventory side of the EventBus wiring.

This use case is called in TWO ways:
  1. Directly via API (manual stock adjustment by warehouse staff)
  2. Via EventBus handler when GoodsReceivedEvent fires from Purchase

The handler function `handle_goods_received_event` is what gets
registered in main.py at startup.

EventBus Wiring Flow:
  Purchase: EventBus.publish("goods_received", payload)
                                    ↓
  EventBus finds registered handlers for "goods_received"
                                    ↓
  handle_goods_received_event(payload) runs ← registered in main.py
                                    ↓
  StockInUseCase.execute() updates inventory
"""

from datetime import datetime
from decimal import Decimal

from app.core.database import SessionLocal
from app.modules.inventory.domain.entities import MovementType, StockMovement
from app.modules.inventory.domain.policies import InventoryPolicy
from app.modules.inventory.infrastructure.repository import InventoryRepository
from sqlalchemy.orm import Session


class StockInUseCase:
    """
    Records stock coming INTO the warehouse.
    Called by the EventBus handler when goods are received from a supplier.
    Can also be called directly for manual stock adjustments.
    """

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = InventoryRepository(db, tenant_id)

    def execute(
        self,
        product_id: int,
        quantity: Decimal,
        reference_type: str,      # "goods_receipt", "manual_adjustment"
        reference_id: int,        # goods_receipt_id or None
        reference_number: str,    # receipt_number
        notes: str = None,
    ) -> StockMovement:

        # ── Step 1: Validate product exists for this tenant ──────────────────
        product = self.repo.get_product(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found for tenant {self.tenant_id}")

        # ── Step 2: Policy check ─────────────────────────────────────────────
        InventoryPolicy.validate_positive_quantity(quantity)

        # ── Step 3: Get current stock ────────────────────────────────────────
        current_stock = self.repo.get_current_stock(product_id)
        new_stock = current_stock + quantity

        # ── Step 4: Create movement record ──────────────────────────────────
        movement = StockMovement(
            id=None,
            tenant_id=self.tenant_id,
            product_id=product_id,
            movement_type=MovementType.IN,
            quantity=quantity,
            stock_before=current_stock,
            stock_after=new_stock,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_number=reference_number,
            notes=notes,
            movement_date=datetime.utcnow(),
        )

        # ── Step 5: Persist movement + update product stock ──────────────────
        saved_movement = self.repo.save_movement(movement)
        self.repo.update_product_stock(product_id, new_stock)

        return saved_movement


# ─── EventBus Handler ────────────────────────────────────────────────────────
#
# This function is what gets REGISTERED in main.py:
#
#   EventBus.subscribe(Events.GOODS_RECEIVED, handle_goods_received_event)
#
# When Purchase fires "goods_received", this runs automatically.
# It uses the SAME db session passed in the event payload so everything
# stays in one transaction.

def handle_goods_received_event(payload: dict) -> None:
    """
    EventBus handler for GoodsReceivedEvent from Purchase module.

    Receives payload dict from GoodsReceivedEvent.to_dict() plus "_db" key.
    Creates a StockMovement(IN) for each product in the receipt.
    """
    # Extract the shared db session (passed by Purchase use case)
    # This ensures Purchase + Inventory run in the SAME db transaction
    db: Session = payload.get("_db")

    if db is None:
        # Fallback: create a new session (e.g. if called from async task)
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        tenant_id = payload["tenant_id"]
        use_case = StockInUseCase(db=db, tenant_id=tenant_id)

        for item in payload["items"]:
            use_case.execute(
                product_id=item["product_id"],
                quantity=Decimal(item["quantity_received"]),
                reference_type="goods_receipt",
                reference_id=payload["goods_receipt_id"],
                reference_number=payload["receipt_number"],
                notes=f"Auto: Goods received from PO #{payload['purchase_order_id']}",
            )

    finally:
        if should_close:
            db.close()

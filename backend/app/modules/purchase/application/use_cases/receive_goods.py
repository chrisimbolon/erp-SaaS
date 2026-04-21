"""
modules/purchase/application/use_cases/receive_goods.py
=========================================================
THE MOST CRITICAL USE CASE IN THE PURCHASE MODULE.

This is where:
  1. Goods receipt is recorded in the DB
  2. PO status is updated
  3. GoodsReceivedEvent is FIRED → Inventory picks it up → stock_in runs

This is the exact wiring point between Purchase and Inventory.
No direct import of Inventory. They communicate only via EventBus.

Flow:
  POST /purchase/goods-receipts
      → ReceiveGoodsUseCase.execute()
          → PurchaseOrderPolicy.can_receive_goods()      [validate]
          → PurchaseOrderPolicy.validate_receipt_quantities() [validate]
          → repository.save_goods_receipt()              [persist]
          → repository.update_po_status()                [persist]
          → EventBus.publish("goods_received", event)    [← THE WIRING]
              → inventory.stock_in() runs automatically
"""

from datetime import datetime
from decimal import Decimal

from app.modules.purchase.application.schemas import (GoodsReceiptResponse,
                                                      ReceiveGoodsRequest)
from app.modules.purchase.domain.entities import (GoodsReceipt,
                                                  GoodsReceiptItem,
                                                  GoodsReceiptStatus, POStatus)
from app.modules.purchase.domain.events import GoodsReceivedEvent, ReceivedItem
from app.modules.purchase.domain.policies import PurchaseOrderPolicy
from app.modules.purchase.infrastructure.repository import PurchaseRepository
from app.shared.events.bus import EventBus, Events
from sqlalchemy.orm import Session


class ReceiveGoodsUseCase:
    """
    Records goods received against a Purchase Order.
    Fires GoodsReceivedEvent so Inventory can update stock.
    """

    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = PurchaseRepository(db, tenant_id)

    def execute(self, request: ReceiveGoodsRequest) -> GoodsReceiptResponse:
        # ── Step 1: Load the PO ──────────────────────────────────────────────
        po = self.repo.get_purchase_order(request.purchase_order_id)
        if not po:
            raise ValueError(f"Purchase Order {request.purchase_order_id} not found")

        # ── Step 2: Policy checks ────────────────────────────────────────────
        if not PurchaseOrderPolicy.can_receive_goods(po):
            raise ValueError(f"Cannot receive goods for PO in status '{po.status}'")

        already_received = self.repo.get_received_quantities(request.purchase_order_id)
        receipt_items = [
            GoodsReceiptItem(
                product_id=item.product_id,
                quantity_received=item.quantity_received,
                purchase_order_item_id=item.purchase_order_item_id,
            )
            for item in request.items
        ]

        errors = PurchaseOrderPolicy.validate_receipt_quantities(po, receipt_items, already_received)
        if errors:
            raise ValueError(f"Receipt validation failed: {'; '.join(errors)}")

        # ── Step 3: Build domain entity ──────────────────────────────────────
        receipt_number = self.repo.generate_receipt_number(self.tenant_id)
        goods_receipt = GoodsReceipt(
            id=None,
            tenant_id=self.tenant_id,
            purchase_order_id=request.purchase_order_id,
            receipt_number=receipt_number,
            items=receipt_items,
            received_date=datetime.utcnow(),
            received_by=self.user_id,
            notes=request.notes,
            status=GoodsReceiptStatus.COMPLETED,
        )

        # ── Step 4: Persist ──────────────────────────────────────────────────
        saved_receipt = self.repo.save_goods_receipt(goods_receipt)

        # Update PO status based on whether fully or partially received
        new_status = self._determine_po_status(po, receipt_items, already_received)
        self.repo.update_po_status(po.id, new_status)

        # ── Step 5: Fire domain event → Inventory will handle stock_in ───────
        #
        # THIS IS THE EVENTBUS WIRING.
        # We don't call inventory directly. We fire an event.
        # Inventory's stock_in handler is registered in main.py lifespan.
        #
        event = GoodsReceivedEvent(
            tenant_id=self.tenant_id,
            purchase_order_id=po.id,
            goods_receipt_id=saved_receipt.id,
            receipt_number=receipt_number,
            supplier_id=po.supplier_id,
            items=[
                ReceivedItem(
                    product_id=item.product_id,
                    quantity_received=item.quantity_received,
                    unit=self._get_unit(po, item.product_id),
                )
                for item in receipt_items
            ],
            received_at=goods_receipt.received_date,
            received_by=self.user_id,
        )

        # db session is passed so inventory handler runs in SAME transaction
        EventBus.publish(Events.GOODS_RECEIVED, {**event.to_dict(), "_db": self.db})

        return GoodsReceiptResponse.model_validate(saved_receipt)

    def _determine_po_status(self, po, receipt_items, already_received) -> POStatus:
        ordered = {item.product_id: item.quantity_ordered for item in po.items}
        new_totals = {
            item.product_id: already_received.get(item.product_id, Decimal(0)) + item.quantity_received
            for item in receipt_items
        }
        all_fulfilled = all(
            new_totals.get(pid, Decimal(0)) >= qty
            for pid, qty in ordered.items()
        )
        return POStatus.FULLY_RECEIVED if all_fulfilled else POStatus.PARTIALLY_RECEIVED

    def _get_unit(self, po, product_id: int) -> str:
        for item in po.items:
            if item.product_id == product_id:
                return item.unit
        return "pcs"

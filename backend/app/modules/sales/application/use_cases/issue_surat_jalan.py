"""
modules/sales/application/use_cases/issue_surat_jalan.py
==========================================================
Issues a Surat Jalan — goods physically leave the warehouse.

This is the "deduct on Surat Jalan" half of the reserve/deduct split.

Flow:
  1. Load SalesOrder → must be CONFIRMED
  2. Create SuratJalan entity
  3. surat_jalan.issue() → status = ISSUED
  4. order.fulfill()     → status = FULFILLED
  5. Persist both
  6. Fire OrderFulfilledEvent
       → Inventory: deduct current_stock + release reservation (atomic)

Why stock deduction happens HERE not on SO confirm:
  Goods are not physically gone until the truck leaves.
  Between SO confirm and SJ issue, the warehouse team picks and packs.
  If anything goes wrong (damaged goods, wrong product), the order
  can still be adjusted before the SJ is issued.
"""

from datetime import datetime
from decimal import Decimal

from app.modules.sales.application.schemas import (IssueSuratJalanRequest,
                                                   SuratJalanResponse)
from app.modules.sales.domain.entities import (SuratJalan, SuratJalanItem,
                                               SuratJalanStatus)
from app.modules.sales.domain.events import FulfilledItem, OrderFulfilledEvent
from app.modules.sales.domain.policies import SalesOrderPolicy
from app.modules.sales.infrastructure.repository import SalesRepository
from app.shared.events.bus import EventBus, Events
from sqlalchemy.orm import Session


class IssueSuratJalanUseCase:

    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = SalesRepository(db, tenant_id)

    def execute(self, request: IssueSuratJalanRequest) -> SuratJalanResponse:

        # ── Step 1: Load order ────────────────────────────────────────────────
        order = self.repo.get_sales_order(request.sales_order_id)
        if not order:
            raise ValueError(f"SalesOrder {request.sales_order_id} not found")

        # ── Step 2: Policy ────────────────────────────────────────────────────
        can, reason = SalesOrderPolicy.can_fulfill(order)
        if not can:
            raise ValueError(reason)

        # ── Step 3: Build Surat Jalan ─────────────────────────────────────────
        sj_number = self.repo.generate_sj_number(self.tenant_id)
        sj_items = [
            SuratJalanItem(
                product_id=item.product_id,
                sales_order_item_id=item.sales_order_item_id,
                quantity_shipped=item.quantity_shipped,
                unit=item.unit,
            )
            for item in request.items
        ]

        surat_jalan = SuratJalan(
            id=None,
            tenant_id=self.tenant_id,
            sales_order_id=order.id,
            sj_number=sj_number,
            status=SuratJalanStatus.DRAFT,
            items=sj_items,
            issued_date=None,
            issued_by=None,
            notes=request.notes,
        )

        # ── Step 4: Issue it ──────────────────────────────────────────────────
        surat_jalan.issue(issued_by=self.user_id)

        # ── Step 5: Fulfill the sales order ───────────────────────────────────
        order.fulfill()

        # ── Step 6: Persist both ──────────────────────────────────────────────
        saved_sj = self.repo.save_surat_jalan(surat_jalan)
        self.repo.update_order_status(order.id, order.status)

        # ── Step 7: Fire OrderFulfilledEvent ──────────────────────────────────
        #
        # Inventory handler will:
        #   → deduct current_stock for each product
        #   → release the active reservation for this order
        #   → write StockMovement(type=OUT) for each item
        #
        # All in the SAME db transaction (we pass self.db).
        # If inventory deduction fails → everything rolls back.
        #
        order_items_map = {item.product_id: item for item in order.items}
        event = OrderFulfilledEvent(
            tenant_id=self.tenant_id,
            sales_order_id=order.id,
            surat_jalan_id=saved_sj.id,
            order_number=order.order_number,
            sj_number=sj_number,
            customer_id=order.customer_id,
            items=[
                FulfilledItem(
                    product_id=sj_item.product_id,
                    quantity=sj_item.quantity_shipped,
                    unit=sj_item.unit,
                    unit_price=order_items_map[sj_item.product_id].unit_price,
                )
                for sj_item in sj_items
            ],
            fulfilled_at=surat_jalan.issued_date,
            fulfilled_by=self.user_id,
        )

        EventBus.publish(Events.ORDER_FULFILLED, {**event.to_dict(), "_db": self.db})

        return SuratJalanResponse.model_validate(saved_sj)

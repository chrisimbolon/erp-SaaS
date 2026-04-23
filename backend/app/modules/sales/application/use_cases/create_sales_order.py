"""
modules/sales/application/use_cases/create_sales_order.py
===========================================================
Creates a SalesOrder in DRAFT status.
No stock interaction yet — that happens on confirm().
"""

from datetime import datetime

from app.modules.sales.application.schemas import (CreateSalesOrderRequest,
                                                   SalesOrderResponse)
from app.modules.sales.domain.entities import (SalesOrder, SalesOrderItem,
                                               SalesOrderStatus)
from app.modules.sales.infrastructure.repository import SalesRepository
from sqlalchemy.orm import Session


class CreateSalesOrderUseCase:

    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = SalesRepository(db, tenant_id)

    def execute(self, request: CreateSalesOrderRequest) -> SalesOrderResponse:
        order_number = self.repo.generate_order_number(self.tenant_id)

        items = [
            SalesOrderItem(
                product_id=i.product_id,
                product_name=i.product_name,
                quantity=i.quantity,
                unit_price=i.unit_price,
                unit=i.unit,
                discount_pct=i.discount_pct,
            )
            for i in request.items
        ]

        order = SalesOrder(
            id=None,
            tenant_id=self.tenant_id,
            customer_id=request.customer_id,
            order_number=order_number,
            status=SalesOrderStatus.DRAFT,
            items=items,
            order_date=datetime.utcnow(),
            notes=request.notes,
            created_by=self.user_id,
        )

        saved = self.repo.save_sales_order(order)
        return SalesOrderResponse.model_validate(saved)

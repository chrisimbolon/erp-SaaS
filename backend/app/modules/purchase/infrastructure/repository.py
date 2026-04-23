"""
modules/purchase/infrastructure/repository.py
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from app.modules.purchase.domain.entities import (GoodsReceipt, POStatus,
                                                  PurchaseOrder,
                                                  PurchaseOrderItem)
from sqlalchemy.orm import Session


class PurchaseRepository:

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    def get_purchase_order(self, po_id: int) -> Optional[PurchaseOrder]:
        from app.modules.purchase.infrastructure.models import (
            PurchaseOrderItemModel, PurchaseOrderModel)
        row = self.db.query(PurchaseOrderModel).filter(
            PurchaseOrderModel.id == po_id,
            PurchaseOrderModel.tenant_id == self.tenant_id
        ).first()
        if not row:
            return None
        items_rows = self.db.query(PurchaseOrderItemModel).filter(
            PurchaseOrderItemModel.purchase_order_id == po_id
        ).all()
        items = [
            PurchaseOrderItem(
                product_id=i.product_id, product_name=i.product_name,
                quantity_ordered=i.quantity_ordered, unit_price=i.unit_price, unit=i.unit
            ) for i in items_rows
        ]
        return PurchaseOrder(
            id=row.id, tenant_id=row.tenant_id, supplier_id=row.supplier_id,
            po_number=row.po_number, status=POStatus(row.status),
            items=items, order_date=row.order_date,
            expected_delivery=row.expected_delivery, notes=row.notes,
        )

    def get_received_quantities(self, po_id: int) -> Dict[int, Decimal]:
        return {}

    def save_goods_receipt(self, receipt: GoodsReceipt):
        from app.modules.purchase.infrastructure.models import \
            GoodsReceiptModel
        row = GoodsReceiptModel(
            tenant_id=receipt.tenant_id, purchase_order_id=receipt.purchase_order_id,
            receipt_number=receipt.receipt_number, status=receipt.status.value,
            received_date=receipt.received_date, received_by=receipt.received_by,
            notes=receipt.notes,
        )
        self.db.add(row)
        self.db.flush()
        receipt.id = row.id
        return receipt

    def update_po_status(self, po_id: int, new_status: POStatus) -> None:
        from app.modules.purchase.infrastructure.models import \
            PurchaseOrderModel
        self.db.query(PurchaseOrderModel).filter(
            PurchaseOrderModel.id == po_id,
            PurchaseOrderModel.tenant_id == self.tenant_id
        ).update({"status": new_status.value})

    def generate_receipt_number(self, tenant_id: int) -> str:
        from app.modules.purchase.infrastructure.models import \
            GoodsReceiptModel
        count = self.db.query(GoodsReceiptModel).filter_by(tenant_id=tenant_id).count()
        now = datetime.utcnow()
        return f"GR/{now.year}/{now.month:02d}/{count+1:04d}"

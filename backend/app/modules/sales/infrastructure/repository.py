"""
modules/sales/infrastructure/repository.py
============================================
All DB write operations for the Sales module.
Read-only queries live in queries.py (CQRS-lite pattern from hr-app).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.modules.sales.domain.entities import (Invoice, InvoiceStatus, Payment,
                                               SalesOrder, SalesOrderItem,
                                               SalesOrderStatus, SuratJalan,
                                               SuratJalanItem,
                                               SuratJalanStatus)
from sqlalchemy.orm import Session


class SalesRepository:

    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # ── Sales Order ───────────────────────────────────────────────────────────

    def get_sales_order(self, order_id: int) -> Optional[SalesOrder]:
        from app.modules.sales.infrastructure.models import (
            SalesOrderItemModel, SalesOrderModel)
        row = self.db.query(SalesOrderModel).filter(
            SalesOrderModel.id == order_id,
            SalesOrderModel.tenant_id == self.tenant_id,
        ).first()
        if not row:
            return None

        item_rows = self.db.query(SalesOrderItemModel).filter(
            SalesOrderItemModel.sales_order_id == order_id
        ).all()

        items = [
            SalesOrderItem(
                product_id=i.product_id, product_name=i.product_name,
                quantity=i.quantity, unit_price=i.unit_price,
                unit=i.unit, discount_pct=i.discount_pct,
            )
            for i in item_rows
        ]

        return SalesOrder(
            id=row.id, tenant_id=row.tenant_id, customer_id=row.customer_id,
            order_number=row.order_number, status=SalesOrderStatus(row.status),
            items=items, order_date=row.order_date,
            notes=row.notes, created_by=row.created_by,
        )

    def save_sales_order(self, order: SalesOrder) -> SalesOrder:
        from app.modules.sales.infrastructure.models import (
            SalesOrderItemModel, SalesOrderModel)
        row = SalesOrderModel(
            tenant_id=order.tenant_id, customer_id=order.customer_id,
            order_number=order.order_number, status=order.status.value,
            order_date=order.order_date, notes=order.notes,
            created_by=order.created_by,
        )
        self.db.add(row)
        self.db.flush()
        order.id = row.id

        for item in order.items:
            item_row = SalesOrderItemModel(
                tenant_id=order.tenant_id, sales_order_id=row.id,
                product_id=item.product_id, product_name=item.product_name,
                quantity=item.quantity, unit_price=item.unit_price,
                unit=item.unit, discount_pct=item.discount_pct,
            )
            self.db.add(item_row)
        self.db.flush()

        return order

    def update_order_status(self, order_id: int, new_status: SalesOrderStatus) -> None:
        from app.modules.sales.infrastructure.models import SalesOrderModel
        self.db.query(SalesOrderModel).filter(
            SalesOrderModel.id == order_id,
            SalesOrderModel.tenant_id == self.tenant_id,
        ).update({"status": new_status.value})

    # ── Surat Jalan ───────────────────────────────────────────────────────────

    def save_surat_jalan(self, sj: SuratJalan) -> SuratJalan:
        from app.modules.sales.infrastructure.models import (
            SuratJalanItemModel, SuratJalanModel)
        row = SuratJalanModel(
            tenant_id=sj.tenant_id, sales_order_id=sj.sales_order_id,
            sj_number=sj.sj_number, status=sj.status.value,
            issued_date=sj.issued_date, issued_by=sj.issued_by, notes=sj.notes,
        )
        self.db.add(row)
        self.db.flush()
        sj.id = row.id

        for item in sj.items:
            item_row = SuratJalanItemModel(
                tenant_id=sj.tenant_id, surat_jalan_id=row.id,
                sales_order_item_id=item.sales_order_item_id,
                product_id=item.product_id,
                quantity_shipped=item.quantity_shipped, unit=item.unit,
            )
            self.db.add(item_row)
        self.db.flush()

        return sj

    # ── Invoice ───────────────────────────────────────────────────────────────

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        from app.modules.sales.infrastructure.models import InvoiceModel
        row = self.db.query(InvoiceModel).filter(
            InvoiceModel.id == invoice_id,
            InvoiceModel.tenant_id == self.tenant_id,
        ).first()
        if not row:
            return None
        return self._row_to_invoice(row)

    def get_invoice_by_order(self, sales_order_id: int) -> Optional[Invoice]:
        from app.modules.sales.infrastructure.models import InvoiceModel
        row = self.db.query(InvoiceModel).filter(
            InvoiceModel.sales_order_id == sales_order_id,
            InvoiceModel.tenant_id == self.tenant_id,
        ).first()
        return self._row_to_invoice(row) if row else None

    def save_invoice(self, invoice: Invoice) -> Invoice:
        from app.modules.sales.infrastructure.models import InvoiceModel
        row = InvoiceModel(
            tenant_id=invoice.tenant_id, sales_order_id=invoice.sales_order_id,
            customer_id=invoice.customer_id, invoice_number=invoice.invoice_number,
            status=invoice.status.value, subtotal=invoice.subtotal,
            tax_amount=invoice.tax_amount, total_amount=invoice.total_amount,
            issue_date=invoice.issue_date, due_date=invoice.due_date,
            notes=invoice.notes,
        )
        self.db.add(row)
        self.db.flush()
        invoice.id = row.id
        return invoice

    def update_invoice_status(self, invoice_id: int, new_status: InvoiceStatus) -> None:
        from app.modules.sales.infrastructure.models import InvoiceModel
        self.db.query(InvoiceModel).filter(
            InvoiceModel.id == invoice_id,
            InvoiceModel.tenant_id == self.tenant_id,
        ).update({"status": new_status.value})

    def _row_to_invoice(self, row) -> Invoice:
        return Invoice(
            id=row.id, tenant_id=row.tenant_id, sales_order_id=row.sales_order_id,
            customer_id=row.customer_id, invoice_number=row.invoice_number,
            status=InvoiceStatus(row.status), subtotal=row.subtotal,
            tax_amount=row.tax_amount, total_amount=row.total_amount,
            issue_date=row.issue_date, due_date=row.due_date, notes=row.notes,
        )

    # ── Payment ───────────────────────────────────────────────────────────────

    def save_payment(self, payment: Payment) -> Payment:
        from app.modules.sales.domain.entities import PaymentMethod
        from app.modules.sales.infrastructure.models import PaymentModel
        row = PaymentModel(
            tenant_id=payment.tenant_id, invoice_id=payment.invoice_id,
            payment_number=payment.payment_number, amount=payment.amount,
            payment_method=payment.payment_method.value,
            payment_date=payment.payment_date,
            reference_no=payment.reference_no, notes=payment.notes,
        )
        self.db.add(row)
        self.db.flush()
        payment.id = row.id
        return payment

    # ── Number generators ─────────────────────────────────────────────────────

    def generate_order_number(self, tenant_id: int) -> str:
        from app.modules.sales.infrastructure.models import SalesOrderModel
        count = self.db.query(SalesOrderModel).filter_by(tenant_id=tenant_id).count()
        now = datetime.utcnow()
        return f"SO/{now.year}/{now.month:02d}/{count+1:04d}"

    def generate_sj_number(self, tenant_id: int) -> str:
        from app.modules.sales.infrastructure.models import SuratJalanModel
        count = self.db.query(SuratJalanModel).filter_by(tenant_id=tenant_id).count()
        now = datetime.utcnow()
        return f"SJ/{now.year}/{now.month:02d}/{count+1:04d}"

    def generate_invoice_number(self, tenant_id: int) -> str:
        from app.modules.sales.infrastructure.models import InvoiceModel
        count = self.db.query(InvoiceModel).filter_by(tenant_id=tenant_id).count()
        now = datetime.utcnow()
        return f"INV/{now.year}/{now.month:02d}/{count+1:04d}"

    def generate_payment_number(self, tenant_id: int) -> str:
        from app.modules.sales.infrastructure.models import PaymentModel
        count = self.db.query(PaymentModel).filter_by(tenant_id=tenant_id).count()
        now = datetime.utcnow()
        return f"PAY/{now.year}/{now.month:02d}/{count+1:04d}"

"""
modules/sales/application/use_cases/create_invoice.py
=======================================================
Creates an Invoice from a fulfilled SalesOrder.

Rules:
  - SalesOrder must be FULFILLED before invoicing
  - One invoice per SalesOrder (enforced by unique constraint)
  - Amounts copied from SalesOrder (subtotal, tax, total)
  - Due date = issue_date + payment_terms_days (default NET 30)
"""

from datetime import datetime

from app.modules.sales.application.schemas import (CreateInvoiceRequest,
                                                   InvoiceResponse)
from app.modules.sales.domain.entities import (Invoice, InvoiceStatus,
                                               SalesOrderStatus)
from app.modules.sales.domain.policies import InvoicePolicy
from app.modules.sales.infrastructure.repository import SalesRepository
from sqlalchemy.orm import Session


class CreateInvoiceUseCase:

    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = SalesRepository(db, tenant_id)

    def execute(self, request: CreateInvoiceRequest) -> InvoiceResponse:

        # ── Load and validate order ───────────────────────────────────────────
        order = self.repo.get_sales_order(request.sales_order_id)
        if not order:
            raise ValueError(f"SalesOrder {request.sales_order_id} not found")

        if order.status != SalesOrderStatus.FULFILLED:
            raise ValueError(
                f"Invoice can only be created for FULFILLED orders. "
                f"Current status: {order.status}. Issue Surat Jalan first."
            )

        # ── Check no duplicate invoice ────────────────────────────────────────
        existing = self.repo.get_invoice_by_order(request.sales_order_id)
        if existing:
            raise ValueError(
                f"Invoice already exists for SalesOrder {request.sales_order_id}: "
                f"{existing.invoice_number}"
            )

        # ── Build invoice ─────────────────────────────────────────────────────
        invoice_number = self.repo.generate_invoice_number(self.tenant_id)
        issue_date = datetime.utcnow()
        payment_terms = request.payment_terms_days or InvoicePolicy.DEFAULT_PAYMENT_TERMS_DAYS
        due_date = InvoicePolicy.calculate_due_date(issue_date, payment_terms)

        invoice = Invoice(
            id=None,
            tenant_id=self.tenant_id,
            sales_order_id=order.id,
            customer_id=order.customer_id,
            invoice_number=invoice_number,
            status=InvoiceStatus.SENT,   # created as SENT (ready to collect)
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            issue_date=issue_date,
            due_date=due_date,
            notes=request.notes,
        )

        saved = self.repo.save_invoice(invoice)
        return InvoiceResponse.model_validate(saved)

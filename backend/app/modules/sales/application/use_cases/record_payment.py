"""
modules/sales/application/use_cases/record_payment.py
=======================================================
Records a payment against an invoice.

For MVP we support full payment only (amount = invoice total).
Partial payments (cicilan) can be added in v2 with a payments
aggregation table and remaining_balance tracking.

On success:
  - Payment row saved
  - Invoice status → PAID
  - (Future: fire PaymentReceivedEvent for accounting module)
"""

from datetime import datetime

from app.modules.sales.application.schemas import (PaymentResponse,
                                                   RecordPaymentRequest)
from app.modules.sales.domain.entities import InvoiceStatus, Payment
from app.modules.sales.domain.policies import InvoicePolicy
from app.modules.sales.infrastructure.repository import SalesRepository
from sqlalchemy.orm import Session


class RecordPaymentUseCase:

    def __init__(self, db: Session, tenant_id: int, user_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = SalesRepository(db, tenant_id)

    def execute(self, request: RecordPaymentRequest) -> PaymentResponse:

        # ── Load invoice ──────────────────────────────────────────────────────
        invoice = self.repo.get_invoice(request.invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {request.invoice_id} not found")

        # ── Policy check ──────────────────────────────────────────────────────
        can, reason = InvoicePolicy.can_record_payment(invoice, request.amount)
        if not can:
            raise ValueError(reason)

        # ── Save payment ──────────────────────────────────────────────────────
        payment_number = self.repo.generate_payment_number(self.tenant_id)

        payment = Payment(
            id=None,
            tenant_id=self.tenant_id,
            invoice_id=invoice.id,
            payment_number=payment_number,
            amount=request.amount,
            payment_method=request.payment_method,
            payment_date=request.payment_date or datetime.utcnow(),
            reference_no=request.reference_no,
            notes=request.notes,
        )

        saved_payment = self.repo.save_payment(payment)

        # ── Mark invoice paid ─────────────────────────────────────────────────
        invoice.mark_paid()
        self.repo.update_invoice_status(invoice.id, invoice.status)

        return PaymentResponse.model_validate(saved_payment)

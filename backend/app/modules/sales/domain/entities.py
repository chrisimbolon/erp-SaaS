"""
modules/sales/domain/entities.py
==================================
Pure Python domain entities for the Sales bounded context.
NO SQLAlchemy. NO FastAPI. Just business objects with behaviour.

Domain model:
  SalesOrder  → contains SalesOrderItems
  SuratJalan  → delivery document, triggers stock deduction
  Invoice     → billing document
  Payment     → recorded against an Invoice

Stock lifecycle:
  SalesOrder.confirm()  → RESERVE stock  (soft lock)
  SuratJalan.issue()    → DEDUCT  stock  (physical OUT)
  SalesOrder.cancel()   → RELEASE reservation (if not yet issued)
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

# ─── Enums ────────────────────────────────────────────────────────────────────

class SalesOrderStatus(str, Enum):
    DRAFT      = "draft"
    CONFIRMED  = "confirmed"      # stock reserved
    FULFILLED  = "fulfilled"      # Surat Jalan issued, stock deducted
    CANCELLED  = "cancelled"      # reservation released


class SuratJalanStatus(str, Enum):
    DRAFT  = "draft"
    ISSUED = "issued"             # goods physically left warehouse


class InvoiceStatus(str, Enum):
    DRAFT    = "draft"
    SENT     = "sent"
    PAID     = "paid"
    OVERDUE  = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    CASH         = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE       = "cheque"
    GIRO         = "giro"


# ─── Value Objects ────────────────────────────────────────────────────────────

@dataclass
class SalesOrderItem:
    product_id:   int
    product_name: str
    quantity:     Decimal
    unit_price:   Decimal
    unit:         str
    discount_pct: Decimal = Decimal("0")   # percentage, e.g. 10 = 10%

    @property
    def subtotal_before_discount(self) -> Decimal:
        return self.quantity * self.unit_price

    @property
    def discount_amount(self) -> Decimal:
        return self.subtotal_before_discount * (self.discount_pct / 100)

    @property
    def subtotal(self) -> Decimal:
        return self.subtotal_before_discount - self.discount_amount


# ─── Aggregates ───────────────────────────────────────────────────────────────

@dataclass
class SalesOrder:
    id:            Optional[int]
    tenant_id:     int
    customer_id:   int
    order_number:  str
    status:        SalesOrderStatus
    items:         List[SalesOrderItem]
    order_date:    datetime
    notes:         Optional[str] = None
    created_by:    int = 0

    # ── Computed ──────────────────────────────────────────────────────────────

    @property
    def subtotal(self) -> Decimal:
        return sum(item.subtotal for item in self.items)

    @property
    def tax_amount(self) -> Decimal:
        """PPN 11% — applied to subtotal after discounts."""
        return (self.subtotal * Decimal("0.11")).quantize(Decimal("0.01"))

    @property
    def total_amount(self) -> Decimal:
        return self.subtotal + self.tax_amount

    # ── Business behaviour ────────────────────────────────────────────────────

    def confirm(self) -> None:
        """
        Confirm the order → status becomes CONFIRMED.
        Caller is responsible for firing StockReservedEvent.
        Business rule: only DRAFT can be confirmed.
        """
        if self.status != SalesOrderStatus.DRAFT:
            raise ValueError(
                f"Cannot confirm SalesOrder in status '{self.status}'. "
                f"Only DRAFT orders can be confirmed."
            )
        self.status = SalesOrderStatus.CONFIRMED

    def fulfill(self) -> None:
        """
        Mark as fulfilled after Surat Jalan is issued.
        Caller fires OrderFulfilledEvent → stock physically deducted.
        Business rule: only CONFIRMED can be fulfilled.
        """
        if self.status != SalesOrderStatus.CONFIRMED:
            raise ValueError(
                f"Cannot fulfill SalesOrder in status '{self.status}'. "
                f"Order must be CONFIRMED first."
            )
        self.status = SalesOrderStatus.FULFILLED

    def cancel(self) -> None:
        """
        Cancel the order.
        If CONFIRMED → caller must fire StockReservationReleasedEvent.
        Business rule: cannot cancel FULFILLED orders.
        """
        if self.status == SalesOrderStatus.FULFILLED:
            raise ValueError(
                "Cannot cancel a fulfilled order. "
                "Create a sales return (retur penjualan) instead."
            )
        if self.status == SalesOrderStatus.CANCELLED:
            raise ValueError("Order is already cancelled.")
        self.status = SalesOrderStatus.CANCELLED


@dataclass
class SuratJalanItem:
    product_id:        int
    sales_order_item_id: int
    quantity_shipped:  Decimal
    unit:              str


@dataclass
class SuratJalan:
    """
    Delivery order / surat jalan.
    When ISSUED → triggers stock OUT via OrderFulfilledEvent.
    """
    id:               Optional[int]
    tenant_id:        int
    sales_order_id:   int
    sj_number:        str
    status:           SuratJalanStatus
    items:            List[SuratJalanItem]
    issued_date:      Optional[datetime]
    issued_by:        Optional[int]       # user_id
    notes:            Optional[str] = None

    def issue(self, issued_by: int) -> None:
        """Issue the Surat Jalan — goods physically leave the warehouse."""
        if self.status == SuratJalanStatus.ISSUED:
            raise ValueError(f"Surat Jalan {self.sj_number} is already issued.")
        self.status     = SuratJalanStatus.ISSUED
        self.issued_date = datetime.utcnow()
        self.issued_by   = issued_by


@dataclass
class Invoice:
    id:             Optional[int]
    tenant_id:      int
    sales_order_id: int
    customer_id:    int
    invoice_number: str
    status:         InvoiceStatus
    subtotal:       Decimal
    tax_amount:     Decimal
    total_amount:   Decimal
    issue_date:     datetime
    due_date:       datetime
    notes:          Optional[str] = None

    @property
    def is_overdue(self) -> bool:
        return (
            self.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED)
            and datetime.utcnow() > self.due_date
        )

    def mark_paid(self) -> None:
        if self.status == InvoiceStatus.PAID:
            raise ValueError("Invoice is already paid.")
        if self.status == InvoiceStatus.CANCELLED:
            raise ValueError("Cannot pay a cancelled invoice.")
        self.status = InvoiceStatus.PAID

    def mark_overdue(self) -> None:
        if self.status == InvoiceStatus.SENT and self.is_overdue:
            self.status = InvoiceStatus.OVERDUE


@dataclass
class Payment:
    id:             Optional[int]
    tenant_id:      int
    invoice_id:     int
    payment_number: str
    amount:         Decimal
    payment_method: PaymentMethod
    payment_date:   datetime
    reference_no:   Optional[str] = None  # bank ref, cheque number etc.
    notes:          Optional[str] = None

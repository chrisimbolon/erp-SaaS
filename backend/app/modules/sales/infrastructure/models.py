"""
modules/sales/infrastructure/models.py
========================================
SQLAlchemy models for Sales module.

Tables:
  sales_orders       → master order record
  sales_order_items  → line items
  surat_jalans       → delivery orders
  surat_jalan_items  → delivery line items
  invoices           → billing documents
  payments           → payment records
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, ForeignKey
from app.shared.models.base import BaseModel


class SalesOrderModel(BaseModel):
    __tablename__ = "sales_orders"

    id           = Column(Integer, primary_key=True)
    customer_id  = Column(Integer, nullable=False, index=True)
    order_number = Column(String(100), nullable=False, unique=True)
    status       = Column(String(50), nullable=False, server_default="draft")
    order_date   = Column(DateTime(timezone=True), nullable=False)
    notes        = Column(Text, nullable=True)
    created_by   = Column(Integer, nullable=False)


class SalesOrderItemModel(BaseModel):
    __tablename__ = "sales_order_items"

    id                  = Column(Integer, primary_key=True)
    sales_order_id      = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    product_id          = Column(Integer, nullable=False)
    product_name        = Column(String(255), nullable=False)
    quantity            = Column(Numeric(12, 3), nullable=False)
    unit_price          = Column(Numeric(15, 2), nullable=False)
    unit                = Column(String(50), nullable=False)
    discount_pct        = Column(Numeric(5, 2), server_default="0", nullable=False)


class SuratJalanModel(BaseModel):
    __tablename__ = "surat_jalans"

    id             = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    sj_number      = Column(String(100), nullable=False, unique=True)
    status         = Column(String(50), nullable=False, server_default="draft")
    issued_date    = Column(DateTime(timezone=True), nullable=True)
    issued_by      = Column(Integer, nullable=True)
    notes          = Column(Text, nullable=True)


class SuratJalanItemModel(BaseModel):
    __tablename__ = "surat_jalan_items"

    id                   = Column(Integer, primary_key=True)
    surat_jalan_id       = Column(Integer, ForeignKey("surat_jalans.id"), nullable=False)
    sales_order_item_id  = Column(Integer, ForeignKey("sales_order_items.id"), nullable=False)
    product_id           = Column(Integer, nullable=False)
    quantity_shipped     = Column(Numeric(12, 3), nullable=False)
    unit                 = Column(String(50), nullable=False)


class InvoiceModel(BaseModel):
    __tablename__ = "invoices"

    id             = Column(Integer, primary_key=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, unique=True)
    customer_id    = Column(Integer, nullable=False, index=True)
    invoice_number = Column(String(100), nullable=False, unique=True)
    status         = Column(String(50), nullable=False, server_default="draft")
    subtotal       = Column(Numeric(15, 2), nullable=False)
    tax_amount     = Column(Numeric(15, 2), nullable=False)
    total_amount   = Column(Numeric(15, 2), nullable=False)
    issue_date     = Column(DateTime(timezone=True), nullable=False)
    due_date       = Column(DateTime(timezone=True), nullable=False)
    notes          = Column(Text, nullable=True)


class PaymentModel(BaseModel):
    __tablename__ = "payments"

    id             = Column(Integer, primary_key=True)
    invoice_id     = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    payment_number = Column(String(100), nullable=False, unique=True)
    amount         = Column(Numeric(15, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    payment_date   = Column(DateTime(timezone=True), nullable=False)
    reference_no   = Column(String(200), nullable=True)
    notes          = Column(Text, nullable=True)

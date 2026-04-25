"""
modules/purchase/infrastructure/models.py
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey
from app.shared.models.base import BaseModel


class PurchaseOrderModel(BaseModel):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, nullable=False, index=True)
    po_number = Column(String(100), nullable=False, unique=True)
    status = Column(String(50), nullable=False, default="draft")
    order_date = Column(DateTime(timezone=True), nullable=False)
    expected_delivery = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)


class PurchaseOrderItemModel(BaseModel):
    __tablename__ = "purchase_order_items"
    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity_ordered = Column(Numeric(12, 3), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    unit = Column(String(50), nullable=False)


class GoodsReceiptModel(BaseModel):
    __tablename__ = "goods_receipts"
    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    receipt_number = Column(String(100), nullable=False, unique=True)
    status = Column(String(50), nullable=False, default="pending")
    received_date = Column(DateTime(timezone=True), nullable=False)
    received_by = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)


class GoodsReceiptItemModel(BaseModel):
    """Line items for each goods receipt — one row per product received."""
    __tablename__ = "goods_receipt_items"
    id                     = Column(Integer, primary_key=True)
    goods_receipt_id       = Column(Integer, ForeignKey("goods_receipts.id"), nullable=False, index=True)
    purchase_order_item_id = Column(Integer, ForeignKey("purchase_order_items.id"), nullable=False)
    product_id             = Column(Integer, nullable=False, index=True)
    quantity_received      = Column(Numeric(12, 3), nullable=False)

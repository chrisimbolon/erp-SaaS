"""
modules/inventory/infrastructure/models.py
============================================
SQLAlchemy models for Inventory.
Domain entities live in domain/entities.py — never import these from domain layer.

Tables:
  products           → master product list with current_stock
  stock_movements    → audit trail of every stock change (immutable)
  stock_reservations → soft locks for confirmed sales orders
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text
from app.shared.models.base import BaseModel


class ProductModel(BaseModel):
    __tablename__ = "products"

    id             = Column(Integer, primary_key=True, index=True)
    sku            = Column(String(100), nullable=False, index=True)
    name           = Column(String(255), nullable=False)
    unit           = Column(String(50), nullable=False)
    current_stock  = Column(Numeric(12, 3), server_default="0", nullable=False)
    minimum_stock  = Column(Numeric(12, 3), server_default="0", nullable=False)
    cost_price     = Column(Numeric(15, 2), server_default="0", nullable=False)
    sell_price     = Column(Numeric(15, 2), server_default="0", nullable=False)
    category_id    = Column(Integer, nullable=True)
    is_active      = Column(Boolean, server_default="true", nullable=False)


class StockMovementModel(BaseModel):
    """
    Immutable audit trail. Never update or delete rows here.
    Every stock change (IN, OUT, adjustment) gets a new row.
    stock_before + stock_after gives full history.
    """
    __tablename__ = "stock_movements"

    id               = Column(Integer, primary_key=True, index=True)
    product_id       = Column(Integer, nullable=False, index=True)
    movement_type    = Column(String(20), nullable=False)    # in, out, adjustment
    quantity         = Column(Numeric(12, 3), nullable=False)
    stock_before     = Column(Numeric(12, 3), nullable=False)
    stock_after      = Column(Numeric(12, 3), nullable=False)
    reference_type   = Column(String(50), nullable=False)    # goods_receipt, sales_order, manual
    reference_id     = Column(Integer, nullable=False)
    reference_number = Column(String(100), nullable=False)
    movement_date    = Column(DateTime(timezone=True), nullable=False)
    notes            = Column(Text, nullable=True)


class StockReservationModel(BaseModel):
    """
    Soft reservations for confirmed sales orders.
    is_active=True  → stock is reserved (order CONFIRMED, not yet fulfilled)
    is_active=False → released (order CANCELLED or FULFILLED)

    Available stock = product.current_stock - SUM(active reservations)
    """
    __tablename__ = "stock_reservations"

    id                = Column(Integer, primary_key=True, index=True)
    product_id        = Column(Integer, nullable=False, index=True)
    sales_order_id    = Column(Integer, nullable=False, index=True)
    order_number      = Column(String(100), nullable=False)
    quantity_reserved = Column(Numeric(12, 3), nullable=False)
    is_active         = Column(Boolean, server_default="true", nullable=False)

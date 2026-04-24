"""
shared/models/base.py
=====================
Every SQLAlchemy model in KLA inherits from BaseModel.
TenantMixin ensures tenant_id is ALWAYS present and indexed.
TimestampMixin gives created_at / updated_at for free.

RULE: No model in any module may skip BaseModel. Ever.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """
    Every row belongs to a tenant. No exceptions.
    tenant_id is always set from JWT — never from request body.
    """
    tenant_id = Column(Integer, nullable=False, index=True)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)


class BaseModel(Base, TenantMixin, TimestampMixin):
    """
    Abstract base for all domain models.
    Usage:
        class PurchaseOrder(BaseModel):
            __tablename__ = "purchase_orders"
            ...
    """
    __abstract__ = True

"""
modules/tenants/infrastructure/models.py
==========================================
SQLAlchemy models for Tenants and Users.

Note: These models do NOT inherit TenantMixin because:
  - Tenant table IS the tenant
  - User table has tenant_id as a regular FK (nullable for SuperAdmin)
"""

from app.shared.models.base import Base, TimestampMixin
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func


class TenantModel(Base, TimestampMixin):
    __tablename__ = "tenants"

    id           = Column(Integer, primary_key=True)
    name         = Column(String(255), nullable=False)
    slug         = Column(String(100), nullable=False, unique=True, index=True)
    status       = Column(String(50), nullable=False, server_default="trial")
    plan         = Column(String(50), nullable=False, server_default="starter")
    owner_email  = Column(String(255), nullable=False)
    phone        = Column(String(50), nullable=True)
    address      = Column(Text, nullable=True)
    npwp         = Column(String(30), nullable=True)
    logo_url     = Column(String(500), nullable=True)


class UserModel(Base, TimestampMixin):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(Integer, nullable=True, index=True)  # NULL = SuperAdmin
    email           = Column(String(255), nullable=False, unique=True, index=True)
    full_name       = Column(String(255), nullable=False)
    role            = Column(String(50), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, server_default="true", nullable=False)
    last_login      = Column(DateTime(timezone=True), nullable=True)

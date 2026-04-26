"""
app/core/dependencies.py
==========================
FastAPI dependency injection.

TenantContext carries everything downstream use cases need:
  tenant_id, user_id, user_role, email, full_name

SuperAdmin: tenant_id = 0 (sentinel — no real tenant)
"""

from dataclasses import dataclass
from typing import Optional

from app.core.database import SessionLocal
from fastapi import Depends, Request
from sqlalchemy.orm import Session


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass
class TenantContext:
    """
    Populated by TenantMiddleware from the decoded JWT.
    Injected via Depends(get_tenant_context) in every route.
    """
    tenant_id: Optional[int]   # None for SuperAdmin
    user_id:   int
    user_role: str
    email:     str
    full_name: str

    @property
    def is_super_admin(self) -> bool:
        return self.tenant_id == 0 or self.tenant_id is None


def get_tenant_context(request: Request) -> TenantContext:
    """
    Extracts the TenantContext set by TenantMiddleware.
    Will raise AttributeError if middleware didn't run —
    which should never happen in production.
    """
    return TenantContext(
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
        user_role=request.state.user_role,
        email=request.state.email,
        full_name=request.state.full_name,
    )

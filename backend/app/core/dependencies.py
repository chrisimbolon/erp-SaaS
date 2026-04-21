"""
app/core/dependencies.py
=========================
FastAPI dependency injection.
Following your hr-app pattern.

Usage in routes:
    @router.post("/purchase-orders")
    def create_po(
        request: Request,
        db: Session = Depends(get_db),
        ctx: TenantContext = Depends(get_tenant_context),
    ):
        use_case = CreatePurchaseOrderUseCase(db, ctx.tenant_id, ctx.user_id)
        ...
"""

from dataclasses import dataclass

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
    """Carries tenant_id, user_id, role — extracted from JWT by middleware."""
    tenant_id: int
    user_id: int
    user_role: str


def get_tenant_context(request: Request) -> TenantContext:
    """
    Dependency that extracts tenant context set by TenantMiddleware.
    Raises AttributeError if middleware didn't run (should never happen in prod).
    """
    return TenantContext(
        tenant_id=request.state.tenant_id,
        user_id=request.state.user_id,
        user_role=request.state.user_role,
    )

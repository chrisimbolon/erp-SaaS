from dataclasses import dataclass
from typing import Optional

from app.core.database import SessionLocal
from fastapi import Depends, Request
from sqlalchemy.orm import Session


# ─────────────────────────────────────────────
# DB DEPENDENCY
# ─────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────
# TENANT CONTEXT
# ─────────────────────────────────────────────
@dataclass
class TenantContext:
    tenant_id: Optional[int]
    user_id: int
    user_role: str
    email: str
    full_name: str

    @property
    def is_super_admin(self) -> bool:
        return self.tenant_id == 0 or self.tenant_id is None


def get_tenant_context(request: Request) -> TenantContext:
    state = request.state

    return TenantContext(
        tenant_id=getattr(state, "tenant_id", None),
        user_id=getattr(state, "user_id", 0),
        user_role=getattr(state, "user_role", ""),
        email=getattr(state, "email", ""),
        full_name=getattr(state, "full_name", ""),
    )
"""
modules/auth/application/schemas.py
"""

from typing import Optional

from app.shared.rbac.permissions import Role
from pydantic import BaseModel, EmailStr, Field

# ─── Login ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    email:        str
    full_name:    str
    role:         str
    tenant_id:    Optional[int] = None


# ─── Tenant Registration ──────────────────────────────────────────────────────

class RegisterTenantRequest(BaseModel):
    company_name:   str   = Field(min_length=2, max_length=255)
    slug:           str   = Field(min_length=2, max_length=100, pattern=r'^[a-z0-9\-]+$')
    owner_name:     str   = Field(min_length=2)
    owner_email:    EmailStr
    owner_password: str   = Field(min_length=8)
    plan:           Optional[str] = "starter"
    phone:          Optional[str] = None
    address:        Optional[str] = None
    npwp:           Optional[str] = None


class RegisterTenantResponse(BaseModel):
    tenant_id:    int
    company_name: str
    slug:         str
    owner_id:     int
    owner_email:  str
    status:       str


# ─── User ─────────────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email:     EmailStr
    full_name: str   = Field(min_length=2)
    password:  str   = Field(min_length=8)
    role:      Role


class UserResponse(BaseModel):
    id:        int
    email:     str
    full_name: str
    role:      Role
    is_active: bool
    tenant_id: Optional[int] = None
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int

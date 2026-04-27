"""
app/core/security.py
=====================
JWT + password hashing.

Uses bcrypt directly (NOT via passlib).
passlib breaks with bcrypt >= 4.0 due to dropped __about__ attribute.
Direct bcrypt is simpler and has no compatibility issues.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from app.core.config import settings
from jose import JWTError, jwt

# ─── Password hashing ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain text password using bcrypt."""
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except Exception:
        return False


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(
    tenant_id: int,
    user_id:   int,
    role:      str,
    email:     str,
    full_name: str,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "tenant_id": tenant_id,
        "user_id":   user_id,
        "role":      role,
        "email":     email,
        "full_name": full_name,
        "exp":       expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as e:
        raise ValueError(f"Invalid or expired token: {e}")

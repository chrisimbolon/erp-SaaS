"""
app/core/security.py
=====================
JWT creation and verification.
Password hashing via bcrypt.

JWT payload structure:
  {
    "tenant_id": int,      # 0 = SuperAdmin
    "user_id":   int,
    "role":      str,
    "email":     str,
    "full_name": str,
    "exp":       timestamp,
  }
"""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from jose import JWTError, jwt
from passlib.context import CryptContext

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


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
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise ValueError(f"Invalid or expired token: {e}")

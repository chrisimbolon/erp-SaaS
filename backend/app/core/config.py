"""
app/core/config.py
"""
import json
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://kla_user:kla_pass@localhost:5432/kla_db"
    SECRET_KEY: str = "dev-secret-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()

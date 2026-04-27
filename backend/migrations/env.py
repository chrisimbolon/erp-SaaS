import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ─────────────────────────────────────────────────────────────
# Load .env (backend/.env)
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

try:
    from dotenv import load_dotenv
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        print(f"[alembic] Loaded .env from {ENV_FILE}")
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────
# Add backend/ to sys.path
# ─────────────────────────────────────────────────────────────
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ─────────────────────────────────────────────────────────────
# Alembic config
# ─────────────────────────────────────────────────────────────
config = context.config

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

config.set_main_option("sqlalchemy.url", DATABASE_URL)
print(f"[alembic] DATABASE_URL = {DATABASE_URL}")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# IMPORTANT: import modules so tables are registered
from app.modules.inventory.infrastructure import models as _
from app.modules.purchase.infrastructure import models as _
from app.modules.sales.infrastructure import models as _
from app.modules.tenants.infrastructure import models as _
# ─────────────────────────────────────────────────────────────
# Import ALL models so Alembic sees metadata
# ─────────────────────────────────────────────────────────────
from app.shared.models.base import Base

target_metadata = Base.metadata

# ─────────────────────────────────────────────────────────────
# OFFLINE
# ─────────────────────────────────────────────────────────────
def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()

# ─────────────────────────────────────────────────────────────
# ONLINE (FIXED)
# ─────────────────────────────────────────────────────────────
def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # 🔥 CRITICAL FIX — ensure commits actually happen
        connection = connection.execution_options(
            isolation_level="AUTOCOMMIT"
        )

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        context.run_migrations()

# ─────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
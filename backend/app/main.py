"""
app/main.py
===========
KLA ERP SaaS — FastAPI entrypoint.

Routers:
  /api/v1/auth       → login, register tenant, user management
  /api/v1/purchase   → PO, goods receipt
  /api/v1/sales      → SO, surat jalan, invoice, payment
  /api/v1/inventory  → products, stock movements

EventBus wiring (complete):
  GOODS_RECEIVED              Purchase → Inventory stock IN
  STOCK_RESERVED              Sales    → Inventory reserve
  ORDER_FULFILLED             Sales    → Inventory stock OUT + release reservation
  STOCK_RESERVATION_RELEASED  Sales    → Inventory release reservation (cancel)
"""

from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.middleware import TenantMiddleware
# ── Routers ───────────────────────────────────────────────────────────────────
from app.modules.auth.presentation.api.v1.routes import router as auth_router
from app.modules.inventory.application.use_cases.release_reservation import \
    handle_release_reservation_event
from app.modules.inventory.application.use_cases.reserve_stock import \
    handle_stock_reserved_event
# ── Inventory event handlers ──────────────────────────────────────────────────
from app.modules.inventory.application.use_cases.stock_in import \
    handle_goods_received_event
from app.modules.inventory.application.use_cases.stock_out import \
    handle_order_fulfilled_event
from app.modules.inventory.presentation.api.v1.routes import \
    router as inventory_router
from app.modules.purchase.presentation.api.v1.routes import \
    router as purchase_router
from app.modules.sales.presentation.api.v1.routes import router as sales_router
from app.shared.events.bus import EventBus, Events
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def register_event_handlers() -> None:
    EventBus.subscribe(Events.GOODS_RECEIVED,             handle_goods_received_event)
    EventBus.subscribe(Events.STOCK_RESERVED,             handle_stock_reserved_event)
    EventBus.subscribe(Events.ORDER_FULFILLED,            handle_order_fulfilled_event)
    EventBus.subscribe(Events.STOCK_RESERVATION_RELEASED, handle_release_reservation_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_event_handlers()
    print(f"[KLA] EventBus ready → {EventBus.registered_events()}")
    yield
    EventBus.clear()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Sistem KLA — PT Kusuma Lestari Agro",
        description="ERP SaaS · Purchase · Sales · Inventory",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TenantMiddleware)

    app.include_router(auth_router,      prefix="/api/v1/auth",      tags=["Auth"])
    app.include_router(purchase_router,  prefix="/api/v1/purchase",  tags=["Purchase"])
    app.include_router(sales_router,     prefix="/api/v1/sales",     tags=["Sales"])
    app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "KLA ERP",
            "events": EventBus.registered_events(),
        }

    return app


app = create_app()

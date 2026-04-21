"""
app/main.py
===========
FastAPI entrypoint. EventBus wiring lives here in lifespan().

Full wiring — 5 subscriptions:

  Purchase fires:
    GOODS_RECEIVED             → Inventory: stock IN
    PURCHASE_ORDER_CANCELLED   → (future handler)

  Sales fires:
    STOCK_RESERVED             → Inventory: create reservation
    ORDER_FULFILLED            → Inventory: deduct stock + release reservation
    STOCK_RESERVATION_RELEASED → Inventory: release reservation (on SO cancel)

This is the ONLY place modules are connected.
All module code is completely unaware of other modules.
"""

from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.middleware import TenantMiddleware
from app.modules.inventory.application.use_cases.release_reservation import \
    handle_release_reservation_event
from app.modules.inventory.application.use_cases.reserve_stock import \
    handle_stock_reserved_event
# ── Import handlers only — never the modules themselves ──────────────────────
from app.modules.inventory.application.use_cases.stock_in import \
    handle_goods_received_event
from app.modules.inventory.application.use_cases.stock_out import \
    handle_order_fulfilled_event
from app.modules.inventory.presentation.api.v1.routes import \
    router as inventory_router
# ── Import routers ────────────────────────────────────────────────────────────
from app.modules.purchase.presentation.api.v1.routes import \
    router as purchase_router
from app.modules.sales.presentation.api.v1.routes import router as sales_router
from app.shared.events.bus import EventBus, Events
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ─── EventBus Registration ────────────────────────────────────────────────────

def register_event_handlers() -> None:
    """
    THE COMPLETE INTER-MODULE WIRING.

    This function is the single source of truth for
    how Purchase and Sales drive Inventory.

    Read this and you understand the entire system.
    """
    # Purchase → Inventory
    EventBus.subscribe(Events.GOODS_RECEIVED, handle_goods_received_event)

    # Sales → Inventory
    EventBus.subscribe(Events.STOCK_RESERVED,             handle_stock_reserved_event)
    EventBus.subscribe(Events.ORDER_FULFILLED,            handle_order_fulfilled_event)
    EventBus.subscribe(Events.STOCK_RESERVATION_RELEASED, handle_release_reservation_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    register_event_handlers()
    print(f"[KLA] EventBus ready → {EventBus.registered_events()}")
    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    EventBus.clear()
    print("[KLA] EventBus cleared.")


# ─── App Factory ──────────────────────────────────────────────────────────────

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

    app.include_router(purchase_router, prefix="/api/v1/purchase",  tags=["Purchase"])
    app.include_router(sales_router,    prefix="/api/v1/sales",     tags=["Sales"])
    app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory"])

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "KLA ERP",
            "events_registered": EventBus.registered_events(),
        }

    return app


app = create_app()

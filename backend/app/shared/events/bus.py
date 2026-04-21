"""
shared/events/bus.py
====================
In-process EventBus for Aktivago modular monolith.   

Full event registry:
  GOODS_RECEIVED              Purchase fires → Inventory stock IN
  ORDER_FULFILLED             Sales fires    → Inventory stock OUT + release reservation
  STOCK_RESERVED              Sales fires    → Inventory creates reservation
  STOCK_RESERVATION_RELEASED  Sales fires    → Inventory releases reservation (on cancel)
  PURCHASE_ORDER_CANCELLED    Purchase fires → (future use)

Upgrade path:
  Replace publish() internals with Redis Streams or Celery
  when you need async, retries, or fan-out across services.
  All handler signatures stay identical — zero changes to callers.
"""

import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    _handlers: Dict[str, List[Callable]] = {}

    @classmethod
    def subscribe(cls, event_name: str, handler: Callable) -> None:
        """Register a handler. Called once at app startup in lifespan()."""
        if event_name not in cls._handlers:
            cls._handlers[event_name] = []
        cls._handlers[event_name].append(handler)
        logger.info(f"[EventBus] '{handler.__name__}' subscribed to '{event_name}'")

    @classmethod
    def publish(cls, event_name: str, payload: Dict[str, Any]) -> None:
        """
        Fire an event synchronously.
        If a handler raises, the error is logged but never re-raised.
        Other handlers in the list still run.
        """
        handlers = cls._handlers.get(event_name, [])
        if not handlers:
            logger.warning(f"[EventBus] No handlers registered for '{event_name}'")
            return
        logger.info(f"[EventBus] Publishing '{event_name}' → {len(handlers)} handler(s)")
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                logger.error(
                    f"[EventBus] Handler '{handler.__name__}' failed: {e}",
                    exc_info=True,
                )

    @classmethod
    def clear(cls) -> None:
        """Reset. Use in tests only."""
        cls._handlers = {}

    @classmethod
    def registered_events(cls) -> List[str]:
        return list(cls._handlers.keys())


class Events:
    # ── Purchase fires ────────────────────────────────────────────────────────
    GOODS_RECEIVED              = "goods_received"
    PURCHASE_ORDER_CANCELLED    = "purchase_order_cancelled"

    # ── Sales fires ───────────────────────────────────────────────────────────
    STOCK_RESERVED              = "stock_reserved"               # SO confirmed
    ORDER_FULFILLED             = "order_fulfilled"              # Surat Jalan issued
    STOCK_RESERVATION_RELEASED  = "stock_reservation_released"  # SO cancelled

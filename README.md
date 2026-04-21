# First potential client to use Sistem KLA — PT Kusuma Lestari Agro

ERP SaaS: Purchase · Sales · Inventory  
Architecture: DDD Modular Monolith · Multi-Tenant · FastAPI + PostgreSQL + Next.js

## Quick Start

```bash
docker-compose up -d
cd backend && alembic upgrade head
python scripts/seed_dev.py
```

API docs: http://localhost:8000/docs  
Frontend: http://localhost:3000

## Module Structure

```
Purchase → fires GoodsReceivedEvent  → Inventory stock IN
Sales    → fires OrderFulfilledEvent → Inventory stock OUT
```

## Key Files

- `app/main.py` — EventBus wiring (lifespan)
- `app/shared/events/bus.py` — EventBus implementation
- `app/modules/purchase/application/use_cases/receive_goods.py` — fires GOODS_RECEIVED
- `app/modules/inventory/application/use_cases/stock_in.py` — handles GOODS_RECEIVED
- `app/modules/sales/domain/events.py` — OrderFulfilledEvent
- `app/modules/inventory/application/use_cases/stock_out.py` — handles ORDER_FULFILLED


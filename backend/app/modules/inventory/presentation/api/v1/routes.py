"""
modules/inventory/presentation/api/v1/routes.py
"""
from app.core.dependencies import TenantContext, get_db, get_tenant_context
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/products")
def list_products(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    from app.modules.inventory.infrastructure.models import ProductModel
    return db.query(ProductModel).filter(
        ProductModel.tenant_id == ctx.tenant_id,
        ProductModel.is_active == True
    ).all()


@router.get("/stock-movements")
def list_stock_movements(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    from app.modules.inventory.infrastructure.models import StockMovementModel
    return db.query(StockMovementModel).filter(
        StockMovementModel.tenant_id == ctx.tenant_id
    ).order_by(StockMovementModel.movement_date.desc()).limit(100).all()

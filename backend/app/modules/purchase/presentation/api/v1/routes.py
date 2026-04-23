"""
modules/purchase/presentation/api/v1/routes.py
"""
from app.core.dependencies import TenantContext, get_db, get_tenant_context
from app.modules.purchase.application.schemas import (GoodsReceiptResponse,
                                                      ReceiveGoodsRequest)
from app.modules.purchase.application.use_cases.receive_goods import \
    ReceiveGoodsUseCase
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/goods-receipts", response_model=GoodsReceiptResponse, status_code=201)
def receive_goods(
    body: ReceiveGoodsRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Record goods received. Automatically updates inventory via EventBus."""
    use_case = ReceiveGoodsUseCase(db=db, tenant_id=ctx.tenant_id, user_id=ctx.user_id)
    result = use_case.execute(body)
    db.commit()
    return result

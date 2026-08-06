from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.schemas.inventory import StockLevel
from app.services.inventory import StockService, get_stock_service

router = APIRouter(prefix="/stock", tags=["inventory"])


@router.get("", response_model=list[StockLevel])
def list_stock(
    service: StockService = Depends(get_stock_service),
    _user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return service.list()

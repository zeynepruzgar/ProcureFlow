from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.schemas.order import Order
from app.services.orders import OrderService, get_order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[Order])
def list_orders(
    service: OrderService = Depends(get_order_service),
    _user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return service.list()


@router.get("/{order_id}", response_model=Order)
def get_order(
    order_id: str,
    service: OrderService = Depends(get_order_service),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    order = service.get(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order

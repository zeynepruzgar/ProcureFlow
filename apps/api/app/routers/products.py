from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.schemas.product import Product, ProductCreate, ProductUpdate
from app.services.products import ProductService, get_product_service

router = APIRouter(prefix="/products", tags=["products"])

# Yazma islemleri icin yetkili roller (bkz. RLS politikalari).
WRITER_ROLES = ("procurement_specialist", "manager", "admin")


@router.get("", response_model=list[Product])
def list_products(
    service: ProductService = Depends(get_product_service),
    _user: CurrentUser = Depends(get_current_user),  # giris zorunlu (okuma herkese acik)
) -> list[dict]:
    return service.list()


@router.get("/{product_id}", response_model=Product)
def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    product = service.get(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
    _user: CurrentUser = Depends(require_roles(*WRITER_ROLES)),  # yalnizca yetkili roller
) -> dict:
    return service.create(payload.model_dump())


@router.patch("/{product_id}", response_model=Product)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
    _user: CurrentUser = Depends(require_roles(*WRITER_ROLES)),
) -> dict:
    # exclude_unset: yalnizca gonderilen alanlari guncelle.
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )
    product = service.update(product_id, data)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.schemas.supplier import Supplier, SupplierCreate, SupplierUpdate
from app.services.suppliers import SupplierService, get_supplier_service

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

WRITER_ROLES = ("procurement_specialist", "manager", "admin")


@router.get("", response_model=list[Supplier])
def list_suppliers(
    service: SupplierService = Depends(get_supplier_service),
    _user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return service.list()


@router.get("/{supplier_id}", response_model=Supplier)
def get_supplier(
    supplier_id: str,
    service: SupplierService = Depends(get_supplier_service),
    _user: CurrentUser = Depends(get_current_user),
) -> dict:
    supplier = service.get(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.post("", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    service: SupplierService = Depends(get_supplier_service),
    _user: CurrentUser = Depends(require_roles(*WRITER_ROLES)),
) -> dict:
    return service.create(payload.model_dump())


@router.patch("/{supplier_id}", response_model=Supplier)
def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    service: SupplierService = Depends(get_supplier_service),
    _user: CurrentUser = Depends(require_roles(*WRITER_ROLES)),
) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update"
        )
    supplier = service.update(supplier_id, data)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier

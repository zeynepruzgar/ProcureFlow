from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, require_roles
from app.schemas.purchase_request import PurchaseRequest
from app.services.purchase_requests import (
    PurchaseRequestService,
    get_purchase_request_service,
)

router = APIRouter(prefix="/purchase-requests", tags=["purchase-requests"])

# API service role ile calisir ve RLS'i BYPASS eder; bu yuzden rol kontrolunu
# burada elle yapmak zorundayiz. Roller, purchase_requests_select RLS
# politikasiyla ayni tutuldu (bkz. supabase/migrations/...rls_policies.sql).
READ_ROLES = ("procurement_specialist", "manager", "admin")


@router.get("", response_model=list[PurchaseRequest])
def list_purchase_requests(
    service: PurchaseRequestService = Depends(get_purchase_request_service),
    _user: CurrentUser = Depends(require_roles(*READ_ROLES)),
) -> list[dict]:
    """Agent'in onaylanan onerilerden urettigi taslak talepler."""
    return service.list()


@router.get("/{request_id}", response_model=PurchaseRequest)
def get_purchase_request(
    request_id: str,
    service: PurchaseRequestService = Depends(get_purchase_request_service),
    _user: CurrentUser = Depends(require_roles(*READ_ROLES)),
) -> dict:
    purchase_request = service.get(request_id)
    if purchase_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request not found"
        )
    return purchase_request

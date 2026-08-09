from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, get_current_user, require_roles
from app.schemas.signal import ScanResult, Signal
from app.services.detection import DetectionService, get_detection_service

router = APIRouter(prefix="/signals", tags=["signals"])

# Tarama tetiklemek yazma islemidir: specialist / manager / admin.
SCAN_ROLES = ("procurement_specialist", "manager", "admin")


@router.get("", response_model=list[Signal])
def list_signals(
    status: str | None = Query(
        default="open",
        description="Filter by status: open, handled, or omit/all for every row",
    ),
    service: DetectionService = Depends(get_detection_service),
    _user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    # status=all -> filtre yok
    filter_status = None if status in (None, "", "all") else status
    return service.list_signals(status=filter_status)


@router.post("/scan", response_model=ScanResult)
def run_scan(
    service: DetectionService = Depends(get_detection_service),
    _user: CurrentUser = Depends(require_roles(*SCAN_ROLES)),
) -> dict:
    """Detection motorunu manuel tetikle (dashboard'daki 'Scan Now').

    Zamanlanmis job (cron) ileride ayni service.scan() metodunu cagiracak.
    """
    return service.scan()

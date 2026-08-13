from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.agent.service import (
    AgentService,
    SignalNotFoundError,
    SignalNotOpenError,
    get_agent_service,
)
from app.core.auth import CurrentUser, get_current_user, require_roles
from app.schemas.recommendation import Recommendation

router = APIRouter(tags=["recommendations"])

# Oneri uretmek bir yazma islemidir: signals/scan ile ayni roller.
AGENT_ROLES = ("procurement_specialist", "manager", "admin")


@router.post(
    "/signals/{signal_id}/recommend",
    response_model=Recommendation,
    status_code=status.HTTP_201_CREATED,
)
def recommend_for_signal(
    signal_id: str,
    service: AgentService = Depends(get_agent_service),
    _user: CurrentUser = Depends(require_roles(*AGENT_ROLES)),
) -> dict:
    """Acik bir sinyal icin agent grafigini calistirir; pending oneri uretir."""
    try:
        return service.run_for_signal(signal_id)
    except SignalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found"
        ) from exc
    except SignalNotOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Signal is not open",
        ) from exc


@router.get("/recommendations", response_model=list[Recommendation])
def list_recommendations(
    status_filter: str | None = Query(default=None, alias="status"),
    service: AgentService = Depends(get_agent_service),
    _user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return service.list_recommendations(status=status_filter)

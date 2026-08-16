from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.agent.service import (
    AgentService,
    RecommendationNotFoundError,
    RecommendationNotPendingError,
    SignalNotFoundError,
    SignalNotOpenError,
    get_agent_service,
)
from app.core.auth import CurrentUser, get_current_user, require_roles
from app.schemas.recommendation import Recommendation, RecommendationDecision

router = APIRouter(tags=["recommendations"])

# Oneri uretmek bir yazma islemidir: signals/scan ile ayni roller.
AGENT_ROLES = ("procurement_specialist", "manager", "admin")

# Onaylama/reddetme yalnizca manager/admin yetkisinde (bkz. docs/DATA_MODEL.md
# rol tablosu: "Manager: Onerileri onayla/reddet").
REVIEW_ROLES = ("manager", "admin")


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


def _decide(
    recommendation_id: str,
    decision: str,
    service: AgentService,
    user: CurrentUser,
) -> dict:
    """approve/reject route'larinin ortak govdesi: grafigi resume eder."""
    try:
        return service.decide_recommendation(recommendation_id, decision, user.id)
    except RecommendationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found"
        ) from exc
    except RecommendationNotPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recommendation is not pending",
        ) from exc


@router.post(
    "/recommendations/{recommendation_id}/approve",
    response_model=RecommendationDecision,
)
def approve_recommendation(
    recommendation_id: str,
    service: AgentService = Depends(get_agent_service),
    user: CurrentUser = Depends(require_roles(*REVIEW_ROLES)),
) -> dict:
    """Bekleyen bir oneriyi onaylar: agent grafigi devam eder, draft
    purchase_request olusur ve sinyal 'handled' olur."""
    return _decide(recommendation_id, "approve", service, user)


@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=RecommendationDecision,
)
def reject_recommendation(
    recommendation_id: str,
    service: AgentService = Depends(get_agent_service),
    user: CurrentUser = Depends(require_roles(*REVIEW_ROLES)),
) -> dict:
    """Bekleyen bir oneriyi reddeder: taslak talep olusmaz, sinyal yine de
    'handled' olur (tekrar ele alinmasi icin yeni bir tarama gerekir)."""
    return _decide(recommendation_id, "reject", service, user)

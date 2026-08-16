from typing import Any, Literal

from pydantic import BaseModel

RecommendationStatus = Literal["pending", "approved", "rejected"]


class Recommendation(BaseModel):
    id: str
    signal_id: str
    agent_run_id: str | None = None
    rationale: str | None = None
    suggested_supplier_id: str | None = None
    suggested_qty: float | None = None
    status: RecommendationStatus
    reviewer_id: str | None = None
    created_at: str | None = None


class PurchaseRequest(BaseModel):
    id: str
    recommendation_id: str
    supplier_id: str | None = None
    lines: list[dict[str, Any]] = []
    status: Literal["draft"] = "draft"
    created_by: str | None = None
    created_at: str | None = None


class RecommendationDecision(BaseModel):
    """approve/reject cevabi: guncel oneri + (onaylandiysa) olusan taslak talep."""

    recommendation: Recommendation
    purchase_request: PurchaseRequest | None = None

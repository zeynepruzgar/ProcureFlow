from typing import Literal

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

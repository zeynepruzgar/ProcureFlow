"""Recommendations API testleri — FakeAgentService ile (gercek DB/LLM yok)."""

import pytest
from fastapi.testclient import TestClient

from app.agent.service import (
    RecommendationNotFoundError,
    RecommendationNotPendingError,
    SignalNotFoundError,
    SignalNotOpenError,
    get_agent_service,
)
from app.core.auth import CurrentUser, get_current_user
from app.main import app

client = TestClient(app)

REC = {
    "id": "rec1",
    "signal_id": "sig1",
    "agent_run_id": "run1",
    "rationale": "Stock is low; an order is advised.",
    "suggested_supplier_id": "s1",
    "suggested_qty": 100,
    "status": "pending",
    "reviewer_id": None,
    "created_at": "2026-08-14T10:00:00Z",
}

PR = {
    "id": "pr1",
    "recommendation_id": "rec1",
    "supplier_id": "s1",
    "lines": [{"product_id": "p1", "qty": 100}],
    "status": "draft",
    "created_by": None,
    "created_at": "2026-08-14T10:05:00Z",
}


class FakeAgentService:
    def __init__(self) -> None:
        self.recommendations = [REC]
        self.run_calls: list[str] = []
        self.decide_calls: list[tuple[str, str, str]] = []
        self.raise_not_found = False
        self.raise_not_open = False
        self.raise_rec_not_found = False
        self.raise_not_pending = False

    def run_for_signal(self, signal_id: str):
        self.run_calls.append(signal_id)
        if self.raise_not_found:
            raise SignalNotFoundError(signal_id)
        if self.raise_not_open:
            raise SignalNotOpenError(signal_id)
        return REC

    def list_recommendations(self, status: str | None = None):
        if status is None:
            return list(self.recommendations)
        return [r for r in self.recommendations if r["status"] == status]

    def decide_recommendation(self, recommendation_id: str, decision: str, reviewer_id: str):
        self.decide_calls.append((recommendation_id, decision, reviewer_id))
        if self.raise_rec_not_found:
            raise RecommendationNotFoundError(recommendation_id)
        if self.raise_not_pending:
            raise RecommendationNotPendingError(recommendation_id)
        status = "approved" if decision == "approve" else "rejected"
        updated = {**REC, "status": status, "reviewer_id": reviewer_id}
        return {
            "recommendation": updated,
            "purchase_request": PR if decision == "approve" else None,
        }


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _use_fake() -> FakeAgentService:
    fake = FakeAgentService()
    app.dependency_overrides[get_agent_service] = lambda: fake
    return fake


def _login_as(role: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="u1", email="u@example.com", role=role
    )


def test_recommend_requires_auth():
    assert client.post("/signals/sig1/recommend").status_code == 401


def test_recommend_forbidden_for_employee():
    _use_fake()
    _login_as("employee")
    assert client.post("/signals/sig1/recommend").status_code == 403


def test_recommend_allowed_for_specialist():
    fake = _use_fake()
    _login_as("procurement_specialist")
    response = client.post("/signals/sig1/recommend")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["suggested_qty"] == 100
    assert fake.run_calls == ["sig1"]


def test_recommend_returns_404_for_unknown_signal():
    fake = _use_fake()
    fake.raise_not_found = True
    _login_as("manager")
    response = client.post("/signals/does-not-exist/recommend")
    assert response.status_code == 404


def test_recommend_returns_409_for_non_open_signal():
    fake = _use_fake()
    fake.raise_not_open = True
    _login_as("manager")
    response = client.post("/signals/sig1/recommend")
    assert response.status_code == 409


def test_list_recommendations_returns_all_for_authenticated_user():
    _use_fake()
    _login_as("employee")
    response = client.get("/recommendations")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "rec1"


def test_list_recommendations_requires_auth():
    assert client.get("/recommendations").status_code == 401


def test_approve_requires_auth():
    assert client.post("/recommendations/rec1/approve").status_code == 401


def test_approve_forbidden_for_specialist():
    _use_fake()
    _login_as("procurement_specialist")
    assert client.post("/recommendations/rec1/approve").status_code == 403


def test_approve_allowed_for_manager_creates_draft_request():
    fake = _use_fake()
    _login_as("manager")
    response = client.post("/recommendations/rec1/approve")
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"]["status"] == "approved"
    assert body["purchase_request"]["status"] == "draft"
    assert fake.decide_calls == [("rec1", "approve", "u1")]


def test_reject_allowed_for_admin_without_draft_request():
    fake = _use_fake()
    _login_as("admin")
    response = client.post("/recommendations/rec1/reject")
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"]["status"] == "rejected"
    assert body["purchase_request"] is None
    assert fake.decide_calls == [("rec1", "reject", "u1")]


def test_approve_returns_404_for_unknown_recommendation():
    fake = _use_fake()
    fake.raise_rec_not_found = True
    _login_as("manager")
    assert client.post("/recommendations/does-not-exist/approve").status_code == 404


def test_approve_returns_409_when_not_pending():
    fake = _use_fake()
    fake.raise_not_pending = True
    _login_as("manager")
    assert client.post("/recommendations/rec1/approve").status_code == 409

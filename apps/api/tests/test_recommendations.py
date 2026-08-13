"""Recommendations API testleri — FakeAgentService ile (gercek DB/LLM yok)."""

import pytest
from fastapi.testclient import TestClient

from app.agent.service import (
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
    "rationale": "Stok dusuk, siparis onerilir.",
    "suggested_supplier_id": "s1",
    "suggested_qty": 100,
    "status": "pending",
    "reviewer_id": None,
    "created_at": "2026-08-14T10:00:00Z",
}


class FakeAgentService:
    def __init__(self) -> None:
        self.recommendations = [REC]
        self.run_calls: list[str] = []
        self.raise_not_found = False
        self.raise_not_open = False

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

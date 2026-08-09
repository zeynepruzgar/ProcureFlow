"""Signals API testleri — FakeDetectionService ile (gercek DB yok)."""

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.services.detection import get_detection_service

client = TestClient(app)


class FakeDetectionService:
    def __init__(self) -> None:
        self.signals = [
            {
                "id": "sig1",
                "type": "low_stock",
                "entity_id": "b1",
                "severity": "high",
                "status": "open",
                "detected_at": "2026-08-09T10:00:00Z",
            }
        ]
        self.scan_calls = 0

    def list_signals(self, status: str | None = "open"):
        if status is None:
            return list(self.signals)
        return [s for s in self.signals if s["status"] == status]

    def scan(self):
        self.scan_calls += 1
        return {
            "created": 1,
            "updated": 0,
            "closed": 0,
            "open_signals": self.list_signals(status="open"),
        }


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _use_fake() -> FakeDetectionService:
    fake = FakeDetectionService()
    app.dependency_overrides[get_detection_service] = lambda: fake
    return fake


def _login_as(role: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="u1", email="u@example.com", role=role
    )


def test_list_signals_requires_auth():
    assert client.get("/signals").status_code == 401


def test_list_signals_returns_open():
    _use_fake()
    _login_as("employee")
    response = client.get("/signals")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["type"] == "low_stock"


def test_scan_forbidden_for_employee():
    _use_fake()
    _login_as("employee")
    assert client.post("/signals/scan").status_code == 403


def test_scan_allowed_for_specialist():
    fake = _use_fake()
    _login_as("procurement_specialist")
    response = client.post("/signals/scan")
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert fake.scan_calls == 1
    assert body["open_signals"][0]["type"] == "low_stock"

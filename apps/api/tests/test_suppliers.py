import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.services.suppliers import get_supplier_service

client = TestClient(app)


class FakeSupplierService:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {
            "s1": {
                "id": "s1",
                "name": "Acme Supplies",
                "contact_email": "sales@acme.example",
                "lead_time_days": 5,
                "is_active": True,
                "created_at": "2026-01-01T00:00:00Z",
            }
        }

    def list(self):
        return list(self.items.values())

    def get(self, supplier_id):
        return self.items.get(supplier_id)

    def create(self, data):
        row = {"id": "s-new", "created_at": "2026-01-01T00:00:00Z", **data}
        self.items[row["id"]] = row
        return row

    def update(self, supplier_id, data):
        if supplier_id not in self.items:
            return None
        self.items[supplier_id].update(data)
        return self.items[supplier_id]


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _use_fake():
    app.dependency_overrides[get_supplier_service] = lambda: FakeSupplierService()


def _login_as(role: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="u1", email="u@example.com", role=role
    )


def test_list_requires_authentication():
    assert client.get("/suppliers").status_code == 401


def test_list_returns_suppliers():
    _use_fake()
    _login_as("employee")
    response = client.get("/suppliers")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Acme Supplies"


def test_create_forbidden_for_employee():
    _use_fake()
    _login_as("employee")
    response = client.post("/suppliers", json={"name": "New Co"})
    assert response.status_code == 403


def test_create_allowed_for_specialist():
    _use_fake()
    _login_as("procurement_specialist")
    response = client.post("/suppliers", json={"name": "New Co"})
    assert response.status_code == 201
    assert response.json()["name"] == "New Co"

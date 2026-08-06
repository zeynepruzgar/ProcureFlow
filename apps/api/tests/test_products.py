import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.services.products import get_product_service

client = TestClient(app)


class FakeProductService:
    """Testlerde gercek Supabase yerine kullanilan bellek-ici sahte servis."""

    def __init__(self) -> None:
        self.items: dict[str, dict] = {
            "p1": {
                "id": "p1",
                "sku": "SKU-1",
                "name": "Widget",
                "unit": "pcs",
                "min_stock_level": 10,
                "reorder_qty": 50,
                "preferred_supplier_id": None,
                "created_at": "2026-01-01T00:00:00Z",
            }
        }

    def list(self):
        return list(self.items.values())

    def get(self, product_id):
        return self.items.get(product_id)

    def create(self, data):
        row = {"id": "p-new", "created_at": "2026-01-01T00:00:00Z", **data}
        self.items[row["id"]] = row
        return row

    def update(self, product_id, data):
        if product_id not in self.items:
            return None
        self.items[product_id].update(data)
        return self.items[product_id]


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _use_fake_service():
    fake = FakeProductService()
    app.dependency_overrides[get_product_service] = lambda: fake
    return fake


def _login_as(role: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="u1", email="u@example.com", role=role
    )


def test_list_requires_authentication():
    # Token yoksa 401 (Supabase'e gidilmez).
    response = client.get("/products")
    assert response.status_code == 401


def test_list_returns_products_when_authenticated():
    _use_fake_service()
    _login_as("employee")
    response = client.get("/products")
    assert response.status_code == 200
    assert response.json()[0]["sku"] == "SKU-1"


def test_get_unknown_product_returns_404():
    _use_fake_service()
    _login_as("employee")
    response = client.get("/products/does-not-exist")
    assert response.status_code == 404


def test_create_forbidden_for_employee():
    _use_fake_service()
    _login_as("employee")
    response = client.post("/products", json={"sku": "SKU-2", "name": "Gadget"})
    assert response.status_code == 403


def test_create_allowed_for_manager():
    _use_fake_service()
    _login_as("manager")
    response = client.post("/products", json={"sku": "SKU-2", "name": "Gadget"})
    assert response.status_code == 201
    assert response.json()["name"] == "Gadget"


def test_update_product_changes_fields():
    _use_fake_service()
    _login_as("admin")
    response = client.patch("/products/p1", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"

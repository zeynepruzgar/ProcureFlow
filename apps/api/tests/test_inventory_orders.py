import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.services.inventory import get_stock_service
from app.services.orders import get_order_service

client = TestClient(app)


class FakeStockService:
    def list(self):
        return [
            {
                "id": "st1",
                "product_id": "p1",
                "location": "main",
                "quantity": 20,
                "updated_at": "2026-01-01T00:00:00Z",
                "product": {
                    "name": "A4 Paper",
                    "sku": "SKU-1001",
                    "min_stock_level": 50,
                    "unit": "pcs",
                },
            }
        ]


class FakeOrderService:
    def list(self):
        return [
            {
                "id": "o1",
                "supplier_id": "s1",
                "status": "open",
                "expected_delivery_date": "2026-01-10",
                "created_at": "2026-01-01T00:00:00Z",
                "supplier": {"name": "Globex Trading"},
            }
        ]

    def get(self, order_id):
        if order_id != "o1":
            return None
        row = self.list()[0]
        row["lines"] = [
            {
                "id": "l1",
                "product_id": "p1",
                "qty": 40,
                "unit_price": 75.0,
                "product": {"name": "Toner", "sku": "SKU-1003"},
            }
        ]
        return row


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _login_as(role: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id="u1", role=role)


def test_stock_requires_auth():
    assert client.get("/stock").status_code == 401


def test_stock_list_returns_items():
    app.dependency_overrides[get_stock_service] = lambda: FakeStockService()
    _login_as("employee")
    response = client.get("/stock")
    assert response.status_code == 200
    assert response.json()[0]["product"]["sku"] == "SKU-1001"


def test_orders_list_returns_items():
    app.dependency_overrides[get_order_service] = lambda: FakeOrderService()
    _login_as("employee")
    response = client.get("/orders")
    assert response.status_code == 200
    assert response.json()[0]["supplier"]["name"] == "Globex Trading"


def test_order_detail_includes_lines():
    app.dependency_overrides[get_order_service] = lambda: FakeOrderService()
    _login_as("employee")
    response = client.get("/orders/o1")
    assert response.status_code == 200
    assert response.json()["lines"][0]["qty"] == 40


def test_order_detail_404():
    app.dependency_overrides[get_order_service] = lambda: FakeOrderService()
    _login_as("employee")
    assert client.get("/orders/unknown").status_code == 404

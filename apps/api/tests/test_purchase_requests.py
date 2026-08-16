"""Taslak satin alma talebi testleri.

Iki katman ayri ayri test edilir:
  1. Servis  — FakeSupabaseClient ile: jsonb `lines` icindeki product_id'lere
     urun adinin dogru eklenip eklenmedigi (en kolay bozulacak yer).
  2. Router  — FakeService ile: rol/auth kurallari.
"""

import copy

import pytest
from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.services.purchase_requests import (
    PurchaseRequestService,
    get_purchase_request_service,
)
from tests.fakes import FakeSupabaseClient

client = TestClient(app)

PR = {
    "id": "pr1",
    "recommendation_id": "rec1",
    "supplier_id": "s1",
    "lines": [{"product_id": "p1", "qty": 200}],
    "status": "draft",
    "created_by": None,
    "created_at": "2026-08-16T10:00:00Z",
}


# ------------------------------------------------------------------
# 1) Servis katmani
# ------------------------------------------------------------------
def _service_with(rows: list[dict]) -> PurchaseRequestService:
    # deepcopy sart: servis `lines` icindeki dict'leri YERINDE degistiriyor
    # (product adini ekliyor). Sig kopya (dict(PR)) ic listeyi paylastigi icin
    # modul seviyesindeki PR sabitini kirletir ve testler siraya bagimli olur.
    fake = FakeSupabaseClient(
        seed={
            "purchase_requests": copy.deepcopy(rows),
            "products": [
                {"id": "p1", "name": "A4 Paper Ream", "sku": "PAP-A4", "unit": "ream"},
                {"id": "p2", "name": "Toner", "sku": "TON-1", "unit": "piece"},
            ],
        }
    )
    return PurchaseRequestService(client=fake)


def test_list_attaches_product_name_to_jsonb_lines():
    service = _service_with([dict(PR)])

    rows = service.list()

    assert len(rows) == 1
    line = rows[0]["lines"][0]
    # Arayuzde uuid yerine urun adi gosterilebilsin diye.
    assert line["product"]["name"] == "A4 Paper Ream"
    assert line["product"]["sku"] == "PAP-A4"
    assert line["qty"] == 200


def test_list_handles_request_without_lines():
    service = _service_with([{**PR, "lines": []}])

    rows = service.list()

    assert rows[0]["lines"] == []


def test_list_leaves_line_untouched_when_product_missing():
    # Urun silinmisse satir yine donmeli, sadece adi olmamali.
    service = _service_with([{**PR, "lines": [{"product_id": "gone", "qty": 5}]}])

    line = service.list()[0]["lines"][0]

    assert "product" not in line
    assert line["qty"] == 5


def test_get_returns_none_for_unknown_id():
    service = _service_with([dict(PR)])
    assert service.get("does-not-exist") is None


# ------------------------------------------------------------------
# 2) Router katmani
# ------------------------------------------------------------------
class FakePurchaseRequestService:
    def list(self):
        return [PR]

    def get(self, request_id: str):
        return PR if request_id == "pr1" else None


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _use_fake():
    app.dependency_overrides[get_purchase_request_service] = (
        lambda: FakePurchaseRequestService()
    )


def _login_as(role: str):
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id="u1", email="u@example.com", role=role
    )


def test_list_requires_auth():
    assert client.get("/purchase-requests").status_code == 401


def test_list_forbidden_for_employee():
    _use_fake()
    _login_as("employee")
    # RLS politikasiyla ayni: employee taslak talepleri goremez.
    assert client.get("/purchase-requests").status_code == 403


def test_list_allowed_for_specialist():
    _use_fake()
    _login_as("procurement_specialist")
    response = client.get("/purchase-requests")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "pr1"
    assert body[0]["status"] == "draft"
    assert body[0]["lines"][0]["qty"] == 200


def test_get_returns_404_for_unknown_id():
    _use_fake()
    _login_as("manager")
    assert client.get("/purchase-requests/nope").status_code == 404

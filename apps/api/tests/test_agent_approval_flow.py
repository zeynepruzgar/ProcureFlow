"""AgentService uctan uca akis testleri (Faz 6): run_for_signal -> interrupt
-> decide_recommendation -> resume.

Gercek DB/LLM/Postgres YOK: FakeSupabaseClient (tests/fakes.py) + sahte bir
chat_model + langgraph'in bellek ici checkpointer'i (InMemorySaver) kullanilir.
Amac, gercek Postgres checkpointer'in davranisini (durdur/kaydet/devam et)
degil, agent grafiginin approval_gate etrafindaki DOGRU akisini dogrulamak:
  - run_for_signal recommendation'i 'pending' yazip DURUR (draft yok, sinyal
    hala 'open').
  - approve -> recommendations.status='approved', purchase_requests(draft)
    olusur, signals.status='handled', audit_log'a iki kayit dusuer.
  - reject  -> recommendations.status='rejected', purchase_request YOK,
    signal yine de 'handled' olur.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver

from app.agent.service import (
    AgentService,
    RecommendationNotPendingError,
)
from tests.fakes import FakeSupabaseClient

PRODUCT = {
    "id": "p1",
    "name": "A4 Paper",
    "reorder_qty": 100,
    "preferred_supplier_id": "s1",
}
SIGNAL = {
    "id": "sig1",
    "type": "low_stock",
    "entity_id": "p1",
    "severity": "high",
    "status": "open",
}
SUPPLIER = {"id": "s1", "name": "Acme Supplies", "lead_time_days": 3, "is_active": True}


class FakeChatModel:
    def invoke(self, _messages):
        class Response:
            content = "Stock is critical; an order should be placed now."

        return Response()


def _make_service() -> AgentService:
    client = FakeSupabaseClient(
        seed={
            "products": [PRODUCT],
            "suppliers": [SUPPLIER],
            "stock_levels": [],
            "purchase_order_lines": [],
            "purchase_orders": [],
            "signals": [dict(SIGNAL)],
        }
    )
    return AgentService(
        client=client, chat_model=FakeChatModel(), checkpointer=InMemorySaver()
    )


def test_run_for_signal_writes_pending_recommendation_and_stops_at_gate():
    service = _make_service()

    rec = service.run_for_signal("sig1")

    assert rec["status"] == "pending"
    assert rec["suggested_qty"] == 100
    assert rec["suggested_supplier_id"] == "s1"
    # Henuz onaylanmadi: taslak talep yok, sinyal hala acik.
    assert service.client.rows("purchase_requests") == []
    signal_row = service.client.rows("signals")[0]
    assert signal_row["status"] == "open"


def test_approve_creates_draft_request_and_closes_signal():
    service = _make_service()
    rec = service.run_for_signal("sig1")

    result = service.decide_recommendation(rec["id"], "approve", "manager-1")

    assert result["recommendation"]["status"] == "approved"
    assert result["recommendation"]["reviewer_id"] == "manager-1"
    assert result["purchase_request"] is not None
    assert result["purchase_request"]["status"] == "draft"
    assert result["purchase_request"]["supplier_id"] == "s1"

    signal_row = service.client.rows("signals")[0]
    assert signal_row["status"] == "handled"

    audit_rows = service.client.rows("audit_log")
    assert len(audit_rows) == 2
    actions = {row["action"] for row in audit_rows}
    assert actions == {"recommendation.approved", "purchase_request.created"}


def test_reject_closes_recommendation_without_draft_request():
    service = _make_service()
    rec = service.run_for_signal("sig1")

    result = service.decide_recommendation(rec["id"], "reject", "manager-1")

    assert result["recommendation"]["status"] == "rejected"
    assert result["purchase_request"] is None
    assert service.client.rows("purchase_requests") == []

    signal_row = service.client.rows("signals")[0]
    assert signal_row["status"] == "handled"

    audit_rows = service.client.rows("audit_log")
    assert len(audit_rows) == 1
    assert audit_rows[0]["action"] == "recommendation.rejected"


def test_decide_twice_raises_not_pending():
    service = _make_service()
    rec = service.run_for_signal("sig1")
    service.decide_recommendation(rec["id"], "approve", "manager-1")

    try:
        service.decide_recommendation(rec["id"], "approve", "manager-1")
        raise AssertionError("expected RecommendationNotPendingError")
    except RecommendationNotPendingError:
        pass

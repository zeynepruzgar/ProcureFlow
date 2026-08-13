"""LangGraph grafigi: sinyal -> baglam topla -> analiz et -> oneri yaz.

Faz 5 kapsami (bkz. docs/ROADMAP.md): grafik write_recommendation'da biter.
Onay kesmesi (interrupt), checkpointer ve audit_log Faz 6/7'de eklenecek;
bu yuzden burada checkpointer YOK — tek istekte bastan sona senkron calisir.

State akisi:
  gather_context -> analyze -> write_recommendation -> END
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from supabase import Client

from app.agent import tools

SEVERITY_LABELS = {"low": "dusuk", "medium": "orta", "high": "yuksek"}
TYPE_LABELS = {
    "low_stock": "dusuk stok",
    "delayed_order": "geciken siparis",
    "price_spike": "fiyat artisi",
}


class AgentState(BaseModel):
    """Grafik boyunca tasinan durum. Her node bir sonraki icin alan doldurur."""

    signal: dict[str, Any]
    run_id: str
    context: dict[str, Any] = {}
    rationale: str = ""
    suggested_supplier_id: str | None = None
    suggested_qty: float | None = None
    recommendation_id: str | None = None


# ---------------------------------------------------------------------
# 1) gather_context: sinyal tipine gore ilgili verileri read-only
#    araclarla (app/agent/tools.py) toplar.
# ---------------------------------------------------------------------
def _gather_context(client: Client, state: AgentState) -> dict[str, Any]:
    signal_type = state.signal["type"]
    entity_id = state.signal["entity_id"]

    if signal_type == "low_stock":
        product = tools.get_product(client, entity_id)
        supplier = None
        if product and product.get("preferred_supplier_id"):
            supplier = tools.get_supplier_info(client, product["preferred_supplier_id"])
        return {
            "product": product,
            "stock": tools.get_stock(client, entity_id),
            "open_orders": tools.get_open_orders(client, entity_id),
            "supplier": supplier,
        }

    if signal_type == "delayed_order":
        order = tools.get_order(client, entity_id)
        lines = tools.get_order_lines(client, entity_id) if order else []
        product = tools.get_product(client, lines[0]["product_id"]) if lines else None
        supplier = (
            tools.get_supplier_info(client, order["supplier_id"])
            if order and order.get("supplier_id")
            else None
        )
        return {
            "order": order,
            "order_lines": lines,
            "product": product,
            "supplier": supplier,
        }

    if signal_type == "price_spike":
        product = tools.get_product(client, entity_id)
        supplier = None
        if product and product.get("preferred_supplier_id"):
            supplier = tools.get_supplier_info(client, product["preferred_supplier_id"])
        return {
            "product": product,
            "price_history": tools.get_supplier_prices(client, entity_id),
            "supplier": supplier,
        }

    raise ValueError(f"Unknown signal type: {signal_type}")


# ---------------------------------------------------------------------
# 2) analyze: miktar/tedarikci KURAL tabanli belirlenir (LLM uydurmaz).
#    LLM yalnizca yapilandirilmis baglamdan kisa bir gerekce metni yazar;
#    LLM erisilemezse kural tabanli bir sablona dusulur (agent akisi
#    Ollama'nin ayakta olmasina bagimli kalmaz).
# ---------------------------------------------------------------------
def rule_based_suggestion(context: dict[str, Any]) -> tuple[float | None, str | None]:
    product = context.get("product") or {}
    qty = product.get("reorder_qty")
    supplier_id = product.get("preferred_supplier_id")
    if not supplier_id:
        supplier = context.get("supplier") or {}
        supplier_id = supplier.get("id")
    return qty, supplier_id


def template_rationale(state: AgentState, qty: float | None, supplier_id: str | None) -> str:
    product = state.context.get("product") or {}
    raw_severity = state.signal.get("severity", "")
    severity = SEVERITY_LABELS.get(raw_severity, raw_severity)
    type_label = TYPE_LABELS.get(state.signal["type"], state.signal["type"])
    name = product.get("name", "bilinmeyen urun")
    supplier = state.context.get("supplier") or {}
    supplier_name = supplier.get("name", "tercih edilen tedarikci")
    return (
        f"{severity.capitalize()} onem seviyesinde bir '{type_label}' sinyali tespit edildi. "
        f"Urun: {name}. Onerilen siparis miktari: {qty if qty is not None else 'belirsiz'}, "
        f"tedarikci: {supplier_name}. "
        "(LLM kullanilamadi; bu gerekce kural tabanli otomatik sablondan uretildi.)"
    )


def build_prompt(state: AgentState, qty: float | None, supplier_id: str | None) -> list:
    system = SystemMessage(
        content=(
            "Sen bir satin alma asistanisin. Sana bir tedarik zinciri sinyali ve "
            "ilgili baglam verilecek. Gorevin: 2-4 cumlelik, Turkce, kisa ve net bir "
            "gerekce metni yazmak. Onerilen miktar ve tedarikci ZATEN kurallarla "
            "belirlendi; bunlari degistirme, sadece neden mantikli oldugunu acikla. "
            "Sayi uydurma, sadece sana verilen baglamdaki bilgileri kullan."
        )
    )
    human = HumanMessage(
        content=(
            f"Sinyal tipi: {state.signal['type']}\n"
            f"Onem: {state.signal.get('severity')}\n"
            f"Baglam: {state.context}\n"
            f"Onerilen miktar: {qty}\n"
            f"Onerilen tedarikci id: {supplier_id}\n"
            "Gerekceyi yaz."
        )
    )
    return [system, human]


def analyze(chat_model: BaseChatModel, state: AgentState) -> dict[str, Any]:
    qty, supplier_id = rule_based_suggestion(state.context)

    try:
        response = chat_model.invoke(build_prompt(state, qty, supplier_id))
        rationale = response.content if hasattr(response, "content") else str(response)
        if not rationale or not rationale.strip():
            raise ValueError("empty LLM response")
    except Exception:  # noqa: BLE001 - LLM erisilemezse kural tabanli sablona dus
        rationale = template_rationale(state, qty, supplier_id)

    return {
        "suggested_qty": qty,
        "suggested_supplier_id": supplier_id,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------
# 3) write_recommendation: recommendations tablosuna 'pending' kayit.
# ---------------------------------------------------------------------
def _write_recommendation(client: Client, state: AgentState) -> dict[str, Any]:
    result = (
        client.table("recommendations")
        .insert(
            {
                "signal_id": state.signal["id"],
                "agent_run_id": state.run_id,
                "rationale": state.rationale,
                "suggested_supplier_id": state.suggested_supplier_id,
                "suggested_qty": state.suggested_qty,
                "status": "pending",
            }
        )
        .execute()
    )
    recommendation_id = result.data[0]["id"] if result.data else None
    return {"recommendation_id": recommendation_id}


def build_graph(client: Client, chat_model: BaseChatModel):
    """State'i client/chat_model'a kapayan (closure) node'larla grafigi kurar."""

    graph = StateGraph(AgentState)
    graph.add_node("gather_context", lambda s: {"context": _gather_context(client, s)})
    graph.add_node("analyze", lambda s: analyze(chat_model, s))
    graph.add_node("write_recommendation", lambda s: _write_recommendation(client, s))

    graph.add_edge(START, "gather_context")
    graph.add_edge("gather_context", "analyze")
    graph.add_edge("analyze", "write_recommendation")
    graph.add_edge("write_recommendation", END)

    return graph.compile()

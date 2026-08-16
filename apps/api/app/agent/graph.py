"""LangGraph grafigi: sinyal -> baglam topla -> analiz et -> oneri yaz ->
yonetici onayini bekle -> taslak talep olustur.

Faz 6 kapsami (bkz. docs/ROADMAP.md, docs/AGENT.md): approval_gate node'u
interrupt() ile grafi durdurur. Bu, normal bir "return" degildir — graph.invoke()
o an icin geri doner ama graf "bitmemis" sayilir; durumu checkpointer'da
(app/agent/checkpointer.py, Postgres) saklanir. Yonetici approve/reject
gonderdiginde AgentService, ayni thread_id (agent_run_id) ile grafi
Command(resume=...) kullanarak KALDIGI YERDEN devam ettirir — write_recommendation
tekrar calismaz, sadece approval_gate'ten sonrasi.

State akisi:
  gather_context -> analyze -> write_recommendation -> approval_gate (interrupt)
    -> [approve] create_draft_request -> finalize -> END
    -> [reject]  close_rejected       -> finalize -> END
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel
from supabase import Client

from app.agent import tools
from app.services.audit import write_audit

# "app.agent.graph" logger'i; seviyesi app/core/logging.py'de LOG_LEVEL ile ayarlanir.
logger = logging.getLogger(__name__)

# Uygulamanin tum runtime metinleri (prompt, log, gerekce) INGILIZCE.
# Sebebi sadece tutarlilik degil: kucuk yerel modeller (llama3.2 gibi) Turkce
# prompt aldiginda diller arasi gecis yapip bozuk metin uretiyor.
# severity degerleri ("low"/"medium"/"high") zaten Ingilizce, ceviri gerekmez.
TYPE_LABELS = {
    "low_stock": "low stock",
    "delayed_order": "delayed order",
    "price_spike": "price spike",
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
    # approval_gate'ten sonra doldurulan alanlar (Faz 6):
    decision: Literal["approve", "reject"] | None = None
    reviewer_id: str | None = None
    purchase_request_id: str | None = None


# ---------------------------------------------------------------------
# Loglama yardimcilari
# ---------------------------------------------------------------------
def _run_prefix(state: AgentState) -> str:
    """Her log satirina calisma kimligi ekler (korelasyon id'si).

    Onay akisi IKI ayri HTTP istegine yayilir (once /recommend, sonra
    /approve). Ayni run_id her iki istegin loglarinda da gorunur; boylece
    terminalde tek bir agent calismasini bastan sona takip edebilirsiniz.
    """
    return f"[run {state.run_id[:8]}]"


def _format_messages(messages: list) -> str:
    """LLM'e giden mesajlari okunur tek bir metne cevirir (DEBUG loglari icin)."""
    return "\n".join(f"--- {m.__class__.__name__} ---\n{m.content}" for m in messages)


# ---------------------------------------------------------------------
# 1) gather_context: sinyal tipine gore ilgili verileri read-only
#    araclarla (app/agent/tools.py) toplar.
# ---------------------------------------------------------------------
def _summarize_context(context: dict[str, Any]) -> str:
    """Baglami tek satirlik ozete indirger (listeler icin sadece kayit sayisi)."""
    parts = []
    for key, value in context.items():
        if isinstance(value, list):
            parts.append(f"{key}={len(value)} rows")
        elif isinstance(value, dict):
            parts.append(f"{key}={value.get('name') or value.get('id') or 'present'}")
        else:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def _gather_context(client: Client, state: AgentState) -> dict[str, Any]:
    signal_type = state.signal["type"]
    entity_id = state.signal["entity_id"]
    prefix = _run_prefix(state)
    logger.info(
        "%s gather_context started (signal_type=%s, entity_id=%s)",
        prefix,
        signal_type,
        entity_id,
    )

    context = _fetch_context(client, signal_type, entity_id)

    # Baglam uzun olabilir (fiyat gecmisi vb.): INFO'da ozet, DEBUG'da tamami.
    logger.info("%s gather_context done -> %s", prefix, _summarize_context(context))
    logger.debug("%s gather_context full payload: %s", prefix, context)
    return context


def _fetch_context(client: Client, signal_type: str, entity_id: str) -> dict[str, Any]:
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
    severity = state.signal.get("severity", "unknown")
    type_label = TYPE_LABELS.get(state.signal["type"], state.signal["type"])
    name = product.get("name", "unknown product")
    supplier = state.context.get("supplier") or {}
    supplier_name = supplier.get("name", "the preferred supplier")
    qty_text = qty if qty is not None else "not determined"
    return (
        f"A '{type_label}' signal was detected with {severity} severity. "
        f"Product: {name}. Suggested order quantity: {qty_text}, supplier: {supplier_name}. "
        "(The LLM was unavailable; this rationale was generated from a rule-based template.)"
    )


def build_facts(state: AgentState, qty: float | None, supplier_id: str | None) -> dict[str, Any]:
    """LLM'e verilecek SADE bilgi fisi.

    Ham DB satirlarini (uuid'ler, created_at, foreign key'ler) modele
    dogrudan vermek kucuk modelleri bogar ve halusinasyonu artirir. Onun
    yerine burada yalnizca gerekcelendirmeye yarayan alanlari, insan
    okunur adlarla topluyoruz. None degerler tamamen atilir ki model
    "bos alan"i doldurmaya calismasin.
    """
    product = state.context.get("product") or {}
    supplier = state.context.get("supplier") or {}

    facts: dict[str, Any] = {
        "issue": TYPE_LABELS.get(state.signal["type"], state.signal["type"]),
        "severity": state.signal.get("severity"),
        "product": product.get("name"),
        "unit": product.get("unit"),
        "minimum_stock_level": product.get("min_stock_level"),
        "suggested_order_quantity": qty,
        "supplier": supplier.get("name"),
        "supplier_lead_time_days": supplier.get("lead_time_days"),
    }

    if stock := state.context.get("stock"):
        facts["current_stock"] = sum(row.get("quantity") or 0 for row in stock)
    if (open_orders := state.context.get("open_orders")) is not None:
        facts["open_orders_for_product"] = len(open_orders)

    if order := state.context.get("order"):
        facts["order_status"] = order.get("status")
        facts["expected_delivery_date"] = order.get("expected_delivery_date")

    # Fiyat artisi sinyalinde modelin "ne kadar artti" diyebilmesi icin
    # tum gecmisi degil, son iki fiyati veriyoruz.
    if price_history := state.context.get("price_history"):
        latest = price_history[-1]
        facts["latest_unit_price"] = latest.get("unit_price")
        facts["latest_price_date"] = latest.get("effective_date")
        if len(price_history) > 1:
            facts["previous_unit_price"] = price_history[-2].get("unit_price")

    return {key: value for key, value in facts.items() if value is not None}


def build_prompt(state: AgentState, qty: float | None, supplier_id: str | None) -> list:
    system = SystemMessage(
        content=(
            "You are a procurement assistant. A purchase recommendation has already "
            "been decided by business rules. Your only job is to write a short "
            "justification for it.\n\n"
            "Rules:\n"
            "- Write 2 to 3 sentences of plain English prose.\n"
            "- The suggested quantity and supplier are final. Do not change them and "
            "do not propose alternatives.\n"
            "- Use only the facts provided. Never invent numbers, dates, prices or names.\n"
            "- Do not use bullet points, headings, markdown or any preamble. "
            "Reply with the justification text only."
        )
    )
    facts = build_facts(state, qty, supplier_id)
    human = HumanMessage(
        content=(
            f"Facts:\n{json.dumps(facts, indent=2, default=str)}\n\n"
            "Write the justification."
        )
    )
    return [system, human]


def analyze(chat_model: BaseChatModel, state: AgentState) -> dict[str, Any]:
    prefix = _run_prefix(state)
    qty, supplier_id = rule_based_suggestion(state.context)
    logger.info(
        "%s analyze: rule-based suggestion ready (qty=%s, supplier_id=%s)",
        prefix,
        qty,
        supplier_id,
    )

    messages = build_prompt(state, qty, supplier_id)
    # Prompt tum baglami icerdigi icin uzun olabilir: sadece LOG_LEVEL=DEBUG'da.
    logger.debug("%s LLM prompt:\n%s", prefix, _format_messages(messages))

    model_name = getattr(chat_model, "model", None) or type(chat_model).__name__
    logger.info("%s calling LLM (model=%s)...", prefix, model_name)

    started = time.perf_counter()
    try:
        response = chat_model.invoke(messages)
        elapsed_ms = (time.perf_counter() - started) * 1000
        rationale = response.content if hasattr(response, "content") else str(response)

        # LLM'in HAM cevabi. repr (%r) kullaniyoruz ki bos/bosluklu cevaplar
        # ('   ' gibi) ve satir sonlari log'da gorunur olsun.
        logger.info(
            "%s LLM responded (%.0f ms, %d chars): %r",
            prefix,
            elapsed_ms,
            len(rationale or ""),
            rationale,
        )

        if not rationale or not rationale.strip():
            raise ValueError("LLM returned an empty response")
    except Exception as exc:  # noqa: BLE001 - LLM erisilemezse kural tabanli sablona dus
        elapsed_ms = (time.perf_counter() - started) * 1000
        # exc_info=True tam traceback'i basar. "Ollama kapali mi, model adi
        # yanlis mi, timeout mu?" sorusunun cevabi burada gorunur — onceden
        # bu hata sessizce yutuluyordu.
        logger.warning(
            "%s LLM call failed (%.0f ms): %s: %s — falling back to rule-based template",
            prefix,
            elapsed_ms,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        rationale = template_rationale(state, qty, supplier_id)

    logger.info("%s analyze done, rationale (%d chars): %s", prefix, len(rationale), rationale)
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
    logger.info(
        "%s write_recommendation: wrote 'pending' recommendation (id=%s)",
        _run_prefix(state),
        recommendation_id,
    )
    return {"recommendation_id": recommendation_id}


# ---------------------------------------------------------------------
# 4) approval_gate: grafi durdurur. interrupt()'a verilen deger, ilk
#    calistirmada graph.invoke()'un donus degerinde "__interrupt__" olarak
#    gorunur (bkz. AgentService.run_for_signal). Devam ettirmede (resume)
#    interrupt() cagrisi, Command(resume=...) ile gonderilen degeri DONDURUR
#    ve node kaldigi yerden (bir sonraki satirdan) devam eder.
# ---------------------------------------------------------------------
def _approval_gate(state: AgentState) -> dict[str, Any]:
    prefix = _run_prefix(state)
    # DIKKAT: interrupt() ONCESINDEKI kod IKI KEZ calisir — bir kez grafik
    # durdurulurken, bir kez de resume edilirken node bastan calistirildigi
    # icin. Bu yuzden interrupt() oncesine YAN ETKI (DB yazma, e-posta vb.)
    # konmamalidir; buradaki gibi yalnizca log/hazirlik olmalidir.
    # Asagidaki satiri log'da iki kez gormeniz normaldir.
    logger.info("%s approval_gate: waiting for manager decision...", prefix)

    decision_payload = interrupt(
        {
            "reason": "manager_approval_required",
            "recommendation_id": state.recommendation_id,
            "signal_type": state.signal["type"],
            "suggested_qty": state.suggested_qty,
            "suggested_supplier_id": state.suggested_supplier_id,
        }
    )

    # Buraya yalnizca resume sirasinda ulasilir.
    logger.info(
        "%s approval_gate: decision received (decision=%s, reviewer_id=%s)",
        prefix,
        decision_payload.get("decision"),
        decision_payload.get("reviewer_id"),
    )
    return {
        "decision": decision_payload["decision"],
        "reviewer_id": decision_payload.get("reviewer_id"),
    }


def _route_after_approval(state: AgentState) -> str:
    return "create_draft_request" if state.decision == "approve" else "close_rejected"


# ---------------------------------------------------------------------
# 5a) create_draft_request: onayda purchase_requests(draft) olusturur ve
#     recommendations.status = 'approved' yapar. Miktar/tedarikci LLM'in
#     degil, analyze() adiminda KURAL ile belirlenen degerlerdir (bkz.
#     docs/AGENT.md guvenlik notu) — burada sadece kaydediyoruz.
# ---------------------------------------------------------------------
def _create_draft_request(client: Client, state: AgentState) -> dict[str, Any]:
    client.table("recommendations").update(
        {"status": "approved", "reviewer_id": state.reviewer_id}
    ).eq("id", state.recommendation_id).execute()

    result = (
        client.table("purchase_requests")
        .insert(
            {
                "recommendation_id": state.recommendation_id,
                "supplier_id": state.suggested_supplier_id,
                "lines": [
                    {
                        "product_id": state.signal.get("entity_id")
                        if state.signal["type"] == "low_stock"
                        else state.context.get("product", {}).get("id"),
                        "qty": state.suggested_qty,
                    }
                ],
                "status": "draft",
                "created_by": None,  # system_agent: henuz ayri bir agent profili yok
            }
        )
        .execute()
    )
    purchase_request_id = result.data[0]["id"] if result.data else None
    logger.info(
        "%s create_draft_request: draft request created (id=%s, supplier_id=%s, qty=%s)",
        _run_prefix(state),
        purchase_request_id,
        state.suggested_supplier_id,
        state.suggested_qty,
    )
    return {"purchase_request_id": purchase_request_id}


# ---------------------------------------------------------------------
# 5b) close_rejected: reddedilen oneriyi 'rejected' yapar; taslak talep yok.
# ---------------------------------------------------------------------
def _close_rejected(client: Client, state: AgentState) -> dict[str, Any]:
    client.table("recommendations").update(
        {"status": "rejected", "reviewer_id": state.reviewer_id}
    ).eq("id", state.recommendation_id).execute()
    logger.info(
        "%s close_rejected: recommendation rejected (id=%s), no draft request created",
        _run_prefix(state),
        state.recommendation_id,
    )
    return {}


# ---------------------------------------------------------------------
# 6) finalize: audit_log'a yaz, sinyali 'handled' yap. Karar bir kullanicidan
#    geldigi icin actor_type='user'; taslak talep dogrudan agent tarafindan
#    yazildigi icin ikinci kayit actor_type='agent'.
# ---------------------------------------------------------------------
def _finalize(client: Client, state: AgentState) -> dict[str, Any]:
    action = "recommendation.approved" if state.decision == "approve" else "recommendation.rejected"
    write_audit(
        client,
        actor_id=state.reviewer_id,
        actor_type="user",
        action=action,
        entity_table="recommendations",
        entity_id=state.recommendation_id,
        before={"status": "pending"},
        after={"status": "approved" if state.decision == "approve" else "rejected"},
    )
    if state.decision == "approve" and state.purchase_request_id:
        write_audit(
            client,
            actor_id=None,
            actor_type="agent",
            action="purchase_request.created",
            entity_table="purchase_requests",
            entity_id=state.purchase_request_id,
            before=None,
            after={
                "recommendation_id": state.recommendation_id,
                "supplier_id": state.suggested_supplier_id,
                "qty": state.suggested_qty,
                "status": "draft",
            },
        )

    client.table("signals").update({"status": "handled"}).eq(
        "id", state.signal["id"]
    ).execute()
    logger.info(
        "%s finalize: audit_log written (%s), signal marked 'handled' (id=%s)",
        _run_prefix(state),
        action,
        state.signal["id"],
    )
    return {}


def build_graph(client: Client, chat_model: BaseChatModel, checkpointer: Any = None):
    """State'i client/chat_model'a kapayan (closure) node'larla grafigi kurar.

    checkpointer verilmezse graf checkpointer'siz derlenir (ornegin saf birim
    testlerinde); interrupt/resume kullanan akislar (AgentService) checkpointer
    GEREKTIRIR, aksi halde graf durumu ilk invoke'dan sonra kaybolur.
    """

    graph = StateGraph(AgentState)
    graph.add_node("gather_context", lambda s: {"context": _gather_context(client, s)})
    graph.add_node("analyze", lambda s: analyze(chat_model, s))
    graph.add_node("write_recommendation", lambda s: _write_recommendation(client, s))
    graph.add_node("approval_gate", _approval_gate)
    graph.add_node("create_draft_request", lambda s: _create_draft_request(client, s))
    graph.add_node("close_rejected", lambda s: _close_rejected(client, s))
    graph.add_node("finalize", lambda s: _finalize(client, s))

    graph.add_edge(START, "gather_context")
    graph.add_edge("gather_context", "analyze")
    graph.add_edge("analyze", "write_recommendation")
    graph.add_edge("write_recommendation", "approval_gate")
    graph.add_conditional_edges(
        "approval_gate",
        _route_after_approval,
        {"create_draft_request": "create_draft_request", "close_rejected": "close_rejected"},
    )
    graph.add_edge("create_draft_request", "finalize")
    graph.add_edge("close_rejected", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)

"""Agent'in 'analyze' adiminin birim testleri — DB yok, gercek LLM yok.

rule_based_suggestion / template_rationale saf fonksiyonlardir (rules.py ile
ayni desen). analyze() ise sahte bir chat_model enjekte edilerek test edilir:
hem basarili LLM cevabi hem de LLM hatasinda sablona dusme (fallback) senaryosu.
"""

from app.agent.graph import (
    AgentState,
    analyze,
    build_facts,
    build_prompt,
    rule_based_suggestion,
    template_rationale,
)

PRODUCT = {
    "id": "p1",
    "name": "A4 Paper",
    "unit": "ream",
    "min_stock_level": 50,
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


class FakeChatModel:
    """chat_model.invoke(...) cagrisini taklit eden minimal test dublesi."""

    def __init__(self, content: str | None = None, raise_error: bool = False):
        self.content = content
        self.raise_error = raise_error
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        if self.raise_error:
            raise ConnectionError("ollama unreachable")

        class Response:
            def __init__(self, content):
                self.content = content

        return Response(self.content)


def test_rule_based_suggestion_uses_product_reorder_qty_and_preferred_supplier():
    context = {"product": PRODUCT}
    qty, supplier_id = rule_based_suggestion(context)
    assert qty == 100
    assert supplier_id == "s1"


def test_rule_based_suggestion_falls_back_to_context_supplier_when_no_preferred():
    context = {
        "product": {"reorder_qty": 20, "preferred_supplier_id": None},
        "supplier": {"id": "s2"},
    }
    qty, supplier_id = rule_based_suggestion(context)
    assert qty == 20
    assert supplier_id == "s2"


def test_rule_based_suggestion_handles_missing_product():
    qty, supplier_id = rule_based_suggestion({})
    assert qty is None
    assert supplier_id is None


def test_template_rationale_mentions_product_and_severity():
    state = AgentState(signal=SIGNAL, run_id="r1", context={"product": PRODUCT})
    text = template_rationale(state, 100, "s1")
    assert "A4 Paper" in text
    assert "100" in text


def test_analyze_uses_llm_response_when_available():
    state = AgentState(signal=SIGNAL, run_id="r1", context={"product": PRODUCT})
    chat_model = FakeChatModel(content="Stock is critically low; ordering now is advised.")

    result = analyze(chat_model, state)

    assert result["suggested_qty"] == 100
    assert result["suggested_supplier_id"] == "s1"
    assert result["rationale"] == "Stock is critically low; ordering now is advised."


def test_analyze_falls_back_to_template_when_llm_fails():
    state = AgentState(signal=SIGNAL, run_id="r1", context={"product": PRODUCT})
    chat_model = FakeChatModel(raise_error=True)

    result = analyze(chat_model, state)

    assert result["suggested_qty"] == 100
    assert "rule-based template" in result["rationale"]


def test_analyze_falls_back_when_llm_returns_empty_content():
    state = AgentState(signal=SIGNAL, run_id="r1", context={"product": PRODUCT})
    chat_model = FakeChatModel(content="   ")

    result = analyze(chat_model, state)

    assert "rule-based template" in result["rationale"]


# ---------------------------------------------------------------------
# build_facts: LLM'e ham DB satirlari yerine sade bir bilgi fisi gider.
# Bu, kucuk modellerde (llama3.2 gibi) cikti kalitesini belirleyen en
# onemli etkendi: uuid/created_at gurultusu halusinasyona yol aciyordu.
# ---------------------------------------------------------------------
SUPPLIER = {"id": "s1", "name": "Acme Supplies", "lead_time_days": 3}


def test_build_facts_uses_human_readable_keys_and_hides_ids():
    state = AgentState(
        signal=SIGNAL,
        run_id="r1",
        context={
            "product": PRODUCT,
            "supplier": SUPPLIER,
            "stock": [{"quantity": 12}, {"quantity": 8}],
            "open_orders": [],
        },
    )

    facts = build_facts(state, 100, "s1")

    assert facts["issue"] == "low stock"
    assert facts["severity"] == "high"
    assert facts["product"] == "A4 Paper"
    assert facts["minimum_stock_level"] == 50
    assert facts["suggested_order_quantity"] == 100
    assert facts["supplier"] == "Acme Supplies"
    assert facts["supplier_lead_time_days"] == 3
    # Lokasyonlara dagilmis stok tek bir toplama indirgenir.
    assert facts["current_stock"] == 20
    assert facts["open_orders_for_product"] == 0
    # uuid'ler modele hic gitmez.
    assert "p1" not in str(facts)
    assert "s1" not in str(facts)


def test_build_facts_drops_missing_fields():
    state = AgentState(signal=SIGNAL, run_id="r1", context={"product": {"name": "Toner"}})

    facts = build_facts(state, None, None)

    assert facts["product"] == "Toner"
    # Deger yoksa anahtar hic bulunmaz; model bos alani doldurmaya calismasin.
    assert "supplier" not in facts
    assert "minimum_stock_level" not in facts
    assert "suggested_order_quantity" not in facts


def test_build_facts_includes_last_two_prices_for_price_spike():
    signal = {**SIGNAL, "type": "price_spike"}
    state = AgentState(
        signal=signal,
        run_id="r1",
        context={
            "product": PRODUCT,
            "price_history": [
                {"unit_price": 10, "effective_date": "2026-06-01"},
                {"unit_price": 12, "effective_date": "2026-07-01"},
                {"unit_price": 18, "effective_date": "2026-08-01"},
            ],
        },
    )

    facts = build_facts(state, 100, "s1")

    assert facts["issue"] == "price spike"
    assert facts["latest_unit_price"] == 18
    assert facts["previous_unit_price"] == 12
    assert facts["latest_price_date"] == "2026-08-01"


def test_prompt_is_english_and_carries_facts_as_json():
    state = AgentState(
        signal=SIGNAL, run_id="r1", context={"product": PRODUCT, "supplier": SUPPLIER}
    )

    system, human = build_prompt(state, 100, "s1")

    assert "procurement assistant" in system.content
    # Miktar/tedarikci kurallarla sabit: model bunlari degistirmemeli.
    assert "Do not change them" in system.content
    assert '"suggested_order_quantity": 100' in human.content
    assert '"supplier": "Acme Supplies"' in human.content

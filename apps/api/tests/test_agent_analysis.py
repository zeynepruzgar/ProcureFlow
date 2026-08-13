"""Agent'in 'analyze' adiminin birim testleri — DB yok, gercek LLM yok.

rule_based_suggestion / template_rationale saf fonksiyonlardir (rules.py ile
ayni desen). analyze() ise sahte bir chat_model enjekte edilerek test edilir:
hem basarili LLM cevabi hem de LLM hatasinda sablona dusme (fallback) senaryosu.
"""

from app.agent.graph import (
    AgentState,
    analyze,
    rule_based_suggestion,
    template_rationale,
)

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
    chat_model = FakeChatModel(content="Stok kritik seviyede, hemen siparis onerilir.")

    result = analyze(chat_model, state)

    assert result["suggested_qty"] == 100
    assert result["suggested_supplier_id"] == "s1"
    assert result["rationale"] == "Stok kritik seviyede, hemen siparis onerilir."


def test_analyze_falls_back_to_template_when_llm_fails():
    state = AgentState(signal=SIGNAL, run_id="r1", context={"product": PRODUCT})
    chat_model = FakeChatModel(raise_error=True)

    result = analyze(chat_model, state)

    assert result["suggested_qty"] == 100
    assert "otomatik sablondan" in result["rationale"]


def test_analyze_falls_back_when_llm_returns_empty_content():
    state = AgentState(signal=SIGNAL, run_id="r1", context={"product": PRODUCT})
    chat_model = FakeChatModel(content="   ")

    result = analyze(chat_model, state)

    assert "otomatik sablondan" in result["rationale"]

"""Agent loglama testleri.

Loglar burada "gorsel bir ayrinti" degil, ISLEVSEL bir gereksinim: LLM
cagrisi sessizce basarisiz olup kural tabanli sablona dustugunde, NEDENINI
ancak log'dan ogrenebiliyoruz. Bu yuzden test ediyoruz.

pytest'in `caplog` fixture'i, testin icinde uretilen log kayitlarini yakalar.
`caplog.set_level(...)` hem seviyeyi ayarlar hem de yakalamayi aktif eder.
"""

from __future__ import annotations

import logging

from app.agent.graph import AgentState, analyze

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
    model = "llama3.2"

    def __init__(self, content: str | None = None, error: Exception | None = None):
        self.content = content
        self.error = error

    def invoke(self, _messages):
        if self.error:
            raise self.error

        class Response:
            def __init__(self, content):
                self.content = content

        return Response(self.content)


def _state() -> AgentState:
    return AgentState(signal=SIGNAL, run_id="abcdef12-3456-7890-aaaa-bbbbbbbbbbbb",
                      context={"product": PRODUCT})


def test_llm_response_is_logged(caplog):
    caplog.set_level(logging.INFO, logger="app.agent.graph")

    analyze(FakeChatModel(content="Stock is critically low."), _state())

    messages = "\n".join(r.getMessage() for r in caplog.records)
    # Model adi, ham cevap ve run_id log'da gorunmeli.
    assert "model=llama3.2" in messages
    assert "Stock is critically low." in messages
    assert "[run abcdef12]" in messages


def test_llm_failure_reason_is_logged_as_warning(caplog):
    caplog.set_level(logging.INFO, logger="app.agent.graph")

    analyze(FakeChatModel(error=ConnectionError("ollama unreachable")), _state())

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    text = warnings[0].getMessage()
    # Hatanin TIPI ve MESAJI log'da olmali; yoksa neden fallback'e dustugunu
    # anlayamayiz.
    assert "ConnectionError" in text
    assert "ollama unreachable" in text
    # exc_info=True sayesinde traceback de kayda eklenmis olmali.
    assert warnings[0].exc_info is not None


def test_empty_llm_response_is_logged_as_warning(caplog):
    caplog.set_level(logging.INFO, logger="app.agent.graph")

    analyze(FakeChatModel(content="   "), _state())

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "empty response" in warnings[0].getMessage()


def test_prompt_is_logged_only_at_debug_level(caplog):
    # INFO seviyesinde prompt basilmamali (uzun ve gurultulu).
    caplog.set_level(logging.INFO, logger="app.agent.graph")
    analyze(FakeChatModel(content="ok"), _state())
    assert "LLM prompt" not in "\n".join(r.getMessage() for r in caplog.records)

    caplog.clear()

    # DEBUG seviyesinde basilmali.
    caplog.set_level(logging.DEBUG, logger="app.agent.graph")
    analyze(FakeChatModel(content="ok"), _state())
    assert "LLM prompt" in "\n".join(r.getMessage() for r in caplog.records)

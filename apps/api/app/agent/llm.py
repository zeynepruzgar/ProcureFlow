"""Saglayici-bagimsiz LLM fabrikasi (bkz. docs/AGENT.md #4).

Tum saglayicilar LangChain'in BaseChatModel arayuzunu paylastigi icin,
graph.py bu fonksiyonun donduregu nesneyi hep ayni sekilde (.invoke(...))
kullanir; saglayici degisince graph kodu degismez.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.core.config import get_settings


def get_chat_model() -> BaseChatModel:
    settings = get_settings()

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.llm_model, base_url=settings.ollama_url)

    # openai / anthropic / groq gibi diger saglayicilar henuz baglanmadi:
    # gerektiginde buraya bir dal eklemek yeterli, graph.py degismez.
    raise NotImplementedError(f"LLM provider not wired yet: {settings.llm_provider}")

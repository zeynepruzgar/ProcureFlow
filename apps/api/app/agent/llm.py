"""Saglayici-bagimsiz LLM fabrikasi (bkz. docs/AGENT.md #4).

Tum saglayicilar LangChain'in BaseChatModel arayuzunu paylastigi icin,
graph.py bu fonksiyonun donduregu nesneyi hep ayni sekilde (.invoke(...))
kullanir; saglayici degisince graph kodu degismez.
"""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def get_chat_model() -> BaseChatModel:
    settings = get_settings()

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        # .env'deki degerleri log'a basmak, "neden fallback'e dustu?" sorusunda
        # ilk bakilacak yer: model adi Ollama'da yuklu mu, URL dogru mu?
        logger.info(
            "Creating chat model: provider=ollama model=%s base_url=%s temperature=%s",
            settings.llm_model,
            settings.ollama_url,
            settings.llm_temperature,
        )
        # temperature: Ollama varsayilani 0.8'dir — yaratici yazim icin iyi,
        # ama bizim istedigimiz "verilen gerceklerden sapmayan" bir metin.
        # Dusuk deger halusinasyonu ve dil karisimini azaltir.
        # num_predict: uretilecek azami token — gerekce 2-3 cumle olmali,
        # model sayfalarca yazip 12 saniye harcamasin.
        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_url,
            temperature=settings.llm_temperature,
            num_predict=settings.llm_max_tokens,
        )

    # openai / anthropic / groq gibi diger saglayicilar henuz baglanmadi:
    # gerektiginde buraya bir dal eklemek yeterli, graph.py degismez.
    raise NotImplementedError(f"LLM provider not wired yet: {settings.llm_provider}")

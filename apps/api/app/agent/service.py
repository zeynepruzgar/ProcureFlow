"""AgentService: bir sinyal icin LangGraph akisini calistirip sonucu dondurur.

DetectionService ile ayni "lazy client" deseni: testler gercek Supabase/LLM
olmadan da servisi (fake client/chat_model enjekte ederek) calistirabilsin.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.language_models import BaseChatModel
from supabase import Client

from app.agent.graph import AgentState, build_graph
from app.agent.llm import get_chat_model
from app.core.supabase_client import get_admin_client


class SignalNotFoundError(Exception):
    pass


class SignalNotOpenError(Exception):
    pass


class AgentService:
    def __init__(
        self,
        client: Client | None = None,
        chat_model: BaseChatModel | None = None,
    ) -> None:
        self._client = client
        self._chat_model = chat_model

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_admin_client()
        return self._client

    @property
    def chat_model(self) -> BaseChatModel:
        if self._chat_model is None:
            self._chat_model = get_chat_model()
        return self._chat_model

    def _get_signal(self, signal_id: str) -> dict[str, Any]:
        result = (
            self.client.table("signals")
            .select("*")
            .eq("id", signal_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise SignalNotFoundError(signal_id)
        return result.data[0]

    def run_for_signal(self, signal_id: str) -> dict[str, Any]:
        """Sinyali bulur, grafigi calistirir, olusan recommendation kaydini donder."""
        signal = self._get_signal(signal_id)
        if signal["status"] != "open":
            raise SignalNotOpenError(signal_id)

        graph = build_graph(self.client, self.chat_model)
        initial_state = AgentState(signal=signal, run_id=str(uuid.uuid4()))
        final_state = graph.invoke(initial_state)

        recommendation_id = final_state["recommendation_id"]
        result = (
            self.client.table("recommendations")
            .select("*")
            .eq("id", recommendation_id)
            .limit(1)
            .execute()
        )
        return result.data[0]

    def list_recommendations(self, status: str | None = None) -> list[dict[str, Any]]:
        query = self.client.table("recommendations").select("*").order(
            "created_at", desc=True
        )
        if status:
            query = query.eq("status", status)
        return query.execute().data or []


def get_agent_service() -> AgentService:
    return AgentService()

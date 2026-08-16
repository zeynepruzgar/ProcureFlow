"""AgentService: bir sinyal icin LangGraph akisini calistirip sonucu dondurur.

DetectionService ile ayni "lazy client" deseni: testler gercek Supabase/LLM
olmadan da servisi (fake client/chat_model/checkpointer enjekte ederek)
calistirabilsin.

Faz 6: grafik artik approval_gate'te interrupt() ile durur (bkz.
app/agent/graph.py). Bu yuzden iki giris noktasi var:
  - run_for_signal:        grafi BASTAN baslatir, approval_gate'te durur.
  - decide_recommendation: grafi, kaydedilmis thread_id (agent_run_id) ile
                            Command(resume=...) kullanarak DEVAM ettirir.
Her iki cagri da ayni thread_id'yi kullanmak zorunda; aksi halde checkpointer
"yeni" bir calisma sanip bastan baslar.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command
from supabase import Client

from app.agent.checkpointer import get_checkpointer
from app.agent.graph import AgentState, build_graph
from app.agent.llm import get_chat_model
from app.core.supabase_client import get_admin_client

logger = logging.getLogger(__name__)


class SignalNotFoundError(Exception):
    pass


class SignalNotOpenError(Exception):
    pass


class RecommendationNotFoundError(Exception):
    pass


class RecommendationNotPendingError(Exception):
    pass


class AgentService:
    def __init__(
        self,
        client: Client | None = None,
        chat_model: BaseChatModel | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._client = client
        self._chat_model = chat_model
        self._checkpointer = checkpointer

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

    @property
    def checkpointer(self) -> BaseCheckpointSaver:
        if self._checkpointer is None:
            self._checkpointer = get_checkpointer()
        return self._checkpointer

    def _build_graph(self):
        return build_graph(self.client, self.chat_model, self.checkpointer)

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

    def _get_recommendation(self, recommendation_id: str) -> dict[str, Any]:
        result = (
            self.client.table("recommendations")
            .select("*")
            .eq("id", recommendation_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            raise RecommendationNotFoundError(recommendation_id)
        return result.data[0]

    def run_for_signal(self, signal_id: str) -> dict[str, Any]:
        """Sinyali bulur, grafigi baslatir; approval_gate'te durur.

        Donen kayit hala 'pending' — onay bekliyor. Bu cagri Faz 5'teki
        API sozlesmesiyle ayni (POST /signals/{id}/recommend cevabi degismedi).
        """
        signal = self._get_signal(signal_id)
        if signal["status"] != "open":
            raise SignalNotOpenError(signal_id)

        run_id = str(uuid.uuid4())
        logger.info(
            "Agent run starting: signal_id=%s type=%s severity=%s run_id=%s",
            signal_id,
            signal.get("type"),
            signal.get("severity"),
            run_id,
        )

        graph = self._build_graph()
        initial_state = AgentState(signal=signal, run_id=run_id)
        config = {"configurable": {"thread_id": run_id}}

        started = time.perf_counter()
        final_state = graph.invoke(initial_state, config=config)
        elapsed_ms = (time.perf_counter() - started) * 1000

        recommendation_id = final_state["recommendation_id"]
        # __interrupt__ anahtari, grafigin approval_gate'te DURDUGUNU gosterir.
        # Yoksa bir sey ters gitmis demektir (grafik beklenmedik sekilde bitmis).
        paused = "__interrupt__" in final_state
        logger.info(
            "Agent run paused at approval gate (%.0f ms): run_id=%s "
            "recommendation_id=%s paused=%s",
            elapsed_ms,
            run_id,
            recommendation_id,
            paused,
        )
        return self._get_recommendation(recommendation_id)

    def decide_recommendation(
        self, recommendation_id: str, decision: str, reviewer_id: str
    ) -> dict[str, Any]:
        """Bekleyen bir oneriyi onaylar/reddeder; grafigi kaldigi yerden devam ettirir.

        Basariliysa (decision == 'approve') sonucta bir purchase_request de
        olusmus olur; reject'te yalnizca recommendation.status degisir.
        """
        recommendation = self._get_recommendation(recommendation_id)
        if recommendation["status"] != "pending":
            raise RecommendationNotPendingError(recommendation_id)

        thread_id = recommendation["agent_run_id"]
        logger.info(
            "Agent run resuming: recommendation_id=%s "
            "decision=%s reviewer_id=%s run_id=%s",
            recommendation_id,
            decision,
            reviewer_id,
            thread_id,
        )

        graph = self._build_graph()
        config = {"configurable": {"thread_id": thread_id}}

        started = time.perf_counter()
        graph.invoke(
            Command(resume={"decision": decision, "reviewer_id": reviewer_id}),
            config=config,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "Agent run completed (%.0f ms): run_id=%s decision=%s",
            elapsed_ms,
            thread_id,
            decision,
        )

        updated_recommendation = self._get_recommendation(recommendation_id)
        purchase_request = None
        if decision == "approve":
            pr_result = (
                self.client.table("purchase_requests")
                .select("*")
                .eq("recommendation_id", recommendation_id)
                .limit(1)
                .execute()
            )
            purchase_request = pr_result.data[0] if pr_result.data else None

        return {
            "recommendation": updated_recommendation,
            "purchase_request": purchase_request,
        }

    def list_recommendations(self, status: str | None = None) -> list[dict[str, Any]]:
        query = self.client.table("recommendations").select("*").order(
            "created_at", desc=True
        )
        if status:
            query = query.eq("status", status)
        return query.execute().data or []


def get_agent_service() -> AgentService:
    return AgentService()

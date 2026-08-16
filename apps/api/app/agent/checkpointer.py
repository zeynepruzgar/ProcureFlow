"""Postgres checkpointer: interrupt() ile duran graf durumunu kaliciliga tasir.

Neden gerekli: approval_gate node'u interrupt() ile grafi durdurdugunda,
LangGraph o ana kadarki state'i (hangi node'da kaldigi dahil) bir yere
yazmak zorunda. Bellekte tutarsak sunucu yeniden baslayinca kaybolur;
onay saatler/gunler surebileceginden gercek bir Postgres checkpointer
kullaniyoruz (ayni DATABASE_URL, supabase/README.md'deki direkt Postgres
baglantisi).

supabase_client.py'deki get_admin_client ile ayni "lazy singleton" deseni:
fonksiyon yalnizca gercekten cagrilinca DB'ye baglanir, boylece env
tanimli olmadan da (auth-only) testler calisabilir.
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings


@lru_cache
def get_checkpointer() -> PostgresSaver:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be set in .env (required by the checkpointer).")

    # autocommit + prepare_threshold=0 + dict_row: PostgresSaver'in bekledigi baglanti sekli.
    pool = ConnectionPool(
        conninfo=settings.database_url,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    checkpointer = PostgresSaver(pool)
    # Checkpoint tablolarini (checkpoints, checkpoint_writes, ...) yoksa olusturur.
    # Idempotent: zaten varsa hicbir sey yapmaz. Uygulama her ac(ilis)ta cagirmak guvenli.
    checkpointer.setup()
    return checkpointer

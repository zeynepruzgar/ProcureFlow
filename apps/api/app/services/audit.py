"""audit_log yazma yardimcisi.

audit_log append-only (bkz. supabase/migrations RLS: sadece insert). Bu
yuzden tek bir fonksiyon yeterli — update/delete yok. Hem kullanici
aksiyonlari (approve/reject) hem agent aksiyonlari (create_draft_request)
ayni fonksiyonu actor_type ile ayirt ederek kullanir.
"""

from __future__ import annotations

from typing import Any, Literal

from supabase import Client

ActorType = Literal["user", "agent"]


def write_audit(
    client: Client,
    *,
    actor_id: str | None,
    actor_type: ActorType,
    action: str,
    entity_table: str | None = None,
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    client.table("audit_log").insert(
        {
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action": action,
            "entity_table": entity_table,
            "entity_id": entity_id,
            "before": before,
            "after": after,
        }
    ).execute()

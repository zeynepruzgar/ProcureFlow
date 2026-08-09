"""Detection motoru: veri cek → kurallari calistir → signals'a yaz.

Idempotency (aynı sorunu iki kez acik sinyal olarak uretmeme):
  DB'de partial unique index var: (type, entity_id) WHERE status='open'.
  Motor da once mevcut acik sinyali kontrol eder:
    - Sorun hâlâ varsa  -> severity/detected_at guncelle (update)
    - Sorun yoksa yeni   -> insert (create)
    - Onceki acik sinyal artik kosulda yoksa -> status='handled' (close)

Boylece "Scan Now"a 10 kez basmak 10 satir üretmez.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from supabase import Client

from app.core.supabase_client import get_admin_client
from app.detection.rules import DetectedIssue, run_all_rules


class DetectionService:
    def __init__(self, client: Client) -> None:
        self.client = client

    # ----- veri cekme -----
    def _fetch_products(self) -> list[dict[str, Any]]:
        return self.client.table("products").select("*").execute().data or []

    def _fetch_stock(self) -> list[dict[str, Any]]:
        return self.client.table("stock_levels").select("*").execute().data or []

    def _fetch_orders(self) -> list[dict[str, Any]]:
        return self.client.table("purchase_orders").select("*").execute().data or []

    def _fetch_price_history(self) -> list[dict[str, Any]]:
        return (
            self.client.table("supplier_price_history").select("*").execute().data
            or []
        )

    def _fetch_open_signals(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("signals")
            .select("*")
            .eq("status", "open")
            .execute()
        )
        return result.data or []

    def list_signals(self, status: str | None = "open") -> list[dict[str, Any]]:
        query = self.client.table("signals").select("*").order(
            "detected_at", desc=True
        )
        if status:
            query = query.eq("status", status)
        return query.execute().data or []

    # ----- ana tarama -----
    def scan(self) -> dict[str, Any]:
        """Kurallari calistirip signals tablosunu senkronize et."""
        issues = run_all_rules(
            products=self._fetch_products(),
            stock_levels=self._fetch_stock(),
            orders=self._fetch_orders(),
            price_history=self._fetch_price_history(),
        )
        return self._sync_signals(issues)

    def _sync_signals(self, issues: list[DetectedIssue]) -> dict[str, Any]:
        """DetectedIssue listesini acik sinyallerle eslestir (create/update/close)."""
        open_signals = self._fetch_open_signals()
        # Anahtar: (type, entity_id) -> mevcut satir
        open_map = {(s["type"], s["entity_id"]): s for s in open_signals}
        issue_keys = {(i.type, i.entity_id) for i in issues}

        created = 0
        updated = 0
        closed = 0
        now = datetime.now(UTC).isoformat()

        for issue in issues:
            key = (issue.type, issue.entity_id)
            existing = open_map.get(key)
            if existing is None:
                self.client.table("signals").insert(
                    {
                        "type": issue.type,
                        "entity_id": issue.entity_id,
                        "severity": issue.severity,
                        "status": "open",
                        "detected_at": now,
                    }
                ).execute()
                created += 1
            else:
                # Ayni sorun hâlâ var: severity degismisse veya tazeleme icin update
                self.client.table("signals").update(
                    {"severity": issue.severity, "detected_at": now}
                ).eq("id", existing["id"]).execute()
                updated += 1

        # Artık tespit edilmeyen acik sinyalleri kapat (handled).
        for key, signal in open_map.items():
            if key not in issue_keys:
                self.client.table("signals").update(
                    {"status": "handled"}
                ).eq("id", signal["id"]).execute()
                closed += 1

        return {
            "created": created,
            "updated": updated,
            "closed": closed,
            "open_signals": self.list_signals(status="open"),
        }


def get_detection_service() -> DetectionService:
    return DetectionService(get_admin_client())

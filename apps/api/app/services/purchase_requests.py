"""Taslak satin alma talepleri icin okuma servisi.

Bu servis YALNIZCA okur. purchase_requests satirlari tek bir yerde uretilir:
agent grafiginin create_draft_request node'u (app/agent/graph.py), yonetici
onayindan sonra. Kullanici veya API dogrudan taslak talep olusturamaz.

OrderService ile ayni desen: lazy client + list/get + factory fonksiyonu.
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from app.core.supabase_client import get_admin_client

# supplier ve recommendation iliskili tablolardan gomulu gelir; boylece
# arayuzde uuid yerine tedarikci adi ve onerinin gerekcesi gosterilebilir.
_SELECT = (
    "*, supplier:suppliers(name, lead_time_days), "
    "recommendation:recommendations(rationale, status, signal_id, suggested_qty)"
)


class PurchaseRequestService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_admin_client()
        return self._client

    def list(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("purchase_requests")
            .select(_SELECT)
            .order("created_at", desc=True)
            .execute()
        )
        return self._attach_product_names(result.data or [])

    def get(self, request_id: str) -> dict[str, Any] | None:
        result = (
            self.client.table("purchase_requests")
            .select(_SELECT)
            .eq("id", request_id)
            .limit(1)
            .execute()
        )
        rows = self._attach_product_names(result.data or [])
        return rows[0] if rows else None

    def _attach_product_names(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """`lines` jsonb'sindeki product_id'lere urun adini ekler.

        lines ayri bir tablo olmadigi icin PostgREST ile join edilemez.
        N+1 sorgu yapmamak icin butun product_id'leri toplayip TEK sorguda
        cekiyoruz, sonra bellekte esliyoruz.
        """
        product_ids = {
            line.get("product_id")
            for row in rows
            for line in (row.get("lines") or [])
            if line.get("product_id")
        }
        if not product_ids:
            return rows

        products = (
            self.client.table("products")
            .select("id, name, sku, unit")
            .in_("id", list(product_ids))
            .execute()
        ).data or []
        by_id = {product["id"]: product for product in products}

        for row in rows:
            for line in row.get("lines") or []:
                product = by_id.get(line.get("product_id"))
                if product:
                    line["product"] = {
                        "name": product.get("name"),
                        "sku": product.get("sku"),
                        "unit": product.get("unit"),
                    }
        return rows


def get_purchase_request_service() -> PurchaseRequestService:
    return PurchaseRequestService()

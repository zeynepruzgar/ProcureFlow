"""Agent icin read-only veri erisim fonksiyonlari.

Bunlar LLM'e "tool-calling" ile baglanmiyor (bkz. docs/AGENT.md notu):
lokal Ollama modellerinin function-calling destegi tutarsiz oldugu icin,
graph.py'deki gather_context node'u bu fonksiyonlari sinyal tipine gore
dogrudan cagirir. LLM sadece hazirlanmis, yapilandirilmis baglami okur.

Hicbiri yazma/silme yapmaz; hepsi ayni admin/service client'i kullanir
(DetectionService._fetch_* ile ayni desen).
"""

from __future__ import annotations

from typing import Any

from supabase import Client


def get_product(client: Client, product_id: str) -> dict[str, Any] | None:
    result = (
        client.table("products").select("*").eq("id", product_id).limit(1).execute()
    )
    return result.data[0] if result.data else None


def get_stock(client: Client, product_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("stock_levels")
        .select("*")
        .eq("product_id", product_id)
        .execute()
    )
    return result.data or []


def get_open_orders(
    client: Client, product_id: str | None = None
) -> list[dict[str, Any]]:
    """Acik (status='open') siparisler.

    product_id verilirse, o urunu iceren siparis satirlari (purchase_order_lines)
    uzerinden ilgili siparislere filtrelenir.
    """
    if product_id is None:
        result = client.table("purchase_orders").select("*").eq(
            "status", "open"
        ).execute()
        return result.data or []

    lines_result = (
        client.table("purchase_order_lines")
        .select("po_id")
        .eq("product_id", product_id)
        .execute()
    )
    po_ids = {row["po_id"] for row in (lines_result.data or []) if row.get("po_id")}
    if not po_ids:
        return []

    result = (
        client.table("purchase_orders")
        .select("*")
        .eq("status", "open")
        .in_("id", list(po_ids))
        .execute()
    )
    return result.data or []


def get_order(client: Client, po_id: str) -> dict[str, Any] | None:
    result = (
        client.table("purchase_orders").select("*").eq("id", po_id).limit(1).execute()
    )
    return result.data[0] if result.data else None


def get_order_lines(client: Client, po_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("purchase_order_lines").select("*").eq("po_id", po_id).execute()
    )
    return result.data or []


def get_supplier_prices(client: Client, product_id: str) -> list[dict[str, Any]]:
    result = (
        client.table("supplier_price_history")
        .select("*")
        .eq("product_id", product_id)
        .order("effective_date")
        .execute()
    )
    return result.data or []


def get_supplier_info(client: Client, supplier_id: str) -> dict[str, Any] | None:
    result = (
        client.table("suppliers").select("*").eq("id", supplier_id).limit(1).execute()
    )
    return result.data[0] if result.data else None

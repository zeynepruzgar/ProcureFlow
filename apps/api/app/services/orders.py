from typing import Any

from supabase import Client

from app.core.supabase_client import get_admin_client


class OrderService:
    def __init__(self, client: Client) -> None:
        self.client = client

    def list(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("purchase_orders")
            .select("*, supplier:suppliers(name)")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get(self, order_id: str) -> dict[str, Any] | None:
        # Tek siparis + tedarikci + satirlar (ve satirlardaki urun bilgisi).
        result = (
            self.client.table("purchase_orders")
            .select(
                "*, supplier:suppliers(name), "
                "lines:purchase_order_lines(id, product_id, qty, unit_price, "
                "product:products(name, sku))"
            )
            .eq("id", order_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None


def get_order_service() -> OrderService:
    return OrderService(get_admin_client())

from typing import Any

from supabase import Client

from app.core.supabase_client import get_admin_client


class StockService:
    def __init__(self, client: Client) -> None:
        self.client = client

    def list(self) -> list[dict[str, Any]]:
        # "product:products(...)" -> her stok satirina iliskili urun bilgisini gomer.
        result = (
            self.client.table("stock_levels")
            .select("*, product:products(name, sku, min_stock_level, unit)")
            .execute()
        )
        return result.data or []


def get_stock_service() -> StockService:
    return StockService(get_admin_client())

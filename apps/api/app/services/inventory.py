from typing import Any

from supabase import Client

from app.core.supabase_client import get_admin_client


class StockService:
    def __init__(self, client: Client | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_admin_client()
        return self._client

    def list(self) -> list[dict[str, Any]]:
        # "product:products(...)" -> her stok satirina iliskili urun bilgisini gomer.
        result = (
            self.client.table("stock_levels")
            .select("*, product:products(name, sku, min_stock_level, unit)")
            .execute()
        )
        return result.data or []


def get_stock_service() -> StockService:
    return StockService()

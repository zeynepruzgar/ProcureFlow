from typing import Any

from supabase import Client

from app.core.supabase_client import get_admin_client

# Service katmani = is mantigi. Router (HTTP) ile veritabani arasinda durur.
# Bu ayrim sayesinde router basit kalir ve test etmesi kolay olur.


class ProductService:
    def __init__(self, client: Client | None = None) -> None:
        # client=None: gercek istemci ilk DB cagrisinda olusturulur.
        # Boylece auth-only testler (401) Supabase env olmadan da gecer.
        self._client = client

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = get_admin_client()
        return self._client

    def list(self) -> list[dict[str, Any]]:
        result = self.client.table("products").select("*").order("name").execute()
        return result.data or []

    def get(self, product_id: str) -> dict[str, Any] | None:
        result = (
            self.client.table("products")
            .select("*")
            .eq("id", product_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("products").insert(data).execute()
        return result.data[0]

    def update(self, product_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        result = (
            self.client.table("products").update(data).eq("id", product_id).execute()
        )
        return result.data[0] if result.data else None


def get_product_service() -> ProductService:
    """Router'in kullanacagi ProductService'i uretir (dependency).

    Testlerde bu bagimlilik sahte bir servisle degistirilebilir.
    Supabase istemcisi burada ACILMAZ; ilk DB kullaniminde acilir.
    """
    return ProductService()

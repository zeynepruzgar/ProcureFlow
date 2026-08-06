from typing import Any

from supabase import Client

from app.core.supabase_client import get_admin_client


class SupplierService:
    def __init__(self, client: Client) -> None:
        self.client = client

    def list(self) -> list[dict[str, Any]]:
        result = self.client.table("suppliers").select("*").order("name").execute()
        return result.data or []

    def get(self, supplier_id: str) -> dict[str, Any] | None:
        result = (
            self.client.table("suppliers")
            .select("*")
            .eq("id", supplier_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self.client.table("suppliers").insert(data).execute()
        return result.data[0]

    def update(self, supplier_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        result = (
            self.client.table("suppliers").update(data).eq("id", supplier_id).execute()
        )
        return result.data[0] if result.data else None


def get_supplier_service() -> SupplierService:
    return SupplierService(get_admin_client())

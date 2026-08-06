from pydantic import BaseModel


# Stok satiri. "product" alani, iliskili urun bilgisini (ad, sku, min seviye)
# gomulu olarak tasir (PostgREST embedding ile).
class StockLevel(BaseModel):
    id: str
    product_id: str
    location: str
    quantity: float
    updated_at: str | None = None
    product: dict | None = None

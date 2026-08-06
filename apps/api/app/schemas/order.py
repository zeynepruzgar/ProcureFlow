from pydantic import BaseModel


class OrderLine(BaseModel):
    id: str
    product_id: str
    qty: float
    unit_price: float
    product: dict | None = None


# Satin alma siparisi. "supplier" (tedarikci adi) ve "lines" (siparis satirlari)
# iliskili tablolardan gomulu gelir.
class Order(BaseModel):
    id: str
    supplier_id: str
    status: str
    expected_delivery_date: str | None = None
    created_at: str | None = None
    supplier: dict | None = None
    lines: list[OrderLine] | None = None

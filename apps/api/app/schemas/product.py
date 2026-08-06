from pydantic import BaseModel, Field

# Pydantic semalar = API'nin giris/cikis "sozlesmesi".
# - ProductCreate: yeni urun olustururken beklenen alanlar.
# - ProductUpdate: guncellemede tum alanlar opsiyonel (sadece degisenler gonderilir).
# - Product: API'nin dondurdugu tam kayit (id ve created_at dahil).


class ProductBase(BaseModel):
    sku: str
    name: str
    unit: str = "pcs"
    min_stock_level: float = Field(default=0, ge=0)  # ge=0 -> negatif olamaz
    reorder_qty: float = Field(default=0, ge=0)
    preferred_supplier_id: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    unit: str | None = None
    min_stock_level: float | None = Field(default=None, ge=0)
    reorder_qty: float | None = Field(default=None, ge=0)
    preferred_supplier_id: str | None = None


class Product(ProductBase):
    id: str
    created_at: str | None = None

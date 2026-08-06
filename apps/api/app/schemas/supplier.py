from pydantic import BaseModel, Field


class SupplierBase(BaseModel):
    name: str
    contact_email: str | None = None
    lead_time_days: int = Field(default=7, ge=0)  # teslim suresi negatif olamaz
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_email: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class Supplier(SupplierBase):
    id: str
    created_at: str | None = None

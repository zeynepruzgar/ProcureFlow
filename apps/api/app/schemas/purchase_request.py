"""Taslak satin alma talebi semalari.

Not: `lines` alani DB'de jsonb'dir (bkz. DATA_MODEL.md). Yani siparis
satirlarindan farkli olarak ayri bir tablo degildir; bu yuzden urun adi
PostgREST join'i ile gelemez, servis katmaninda elle eklenir
(app/services/purchase_requests.py).
"""

from typing import Literal

from pydantic import BaseModel


class PurchaseRequestLine(BaseModel):
    product_id: str | None = None
    qty: float | None = None
    # Servis katmaninda doldurulur: {"name": ..., "sku": ..., "unit": ...}
    product: dict | None = None


class PurchaseRequest(BaseModel):
    id: str
    recommendation_id: str
    supplier_id: str | None = None
    lines: list[PurchaseRequestLine] = []
    # Ilk surumde yalnizca 'draft'. Agent GERCEK siparis olusturamaz.
    status: Literal["draft"] = "draft"
    created_by: str | None = None
    created_at: str | None = None
    # Iliskili tablolardan gomulu gelenler (liste ucunda doldurulur; onay
    # cevabinda bos kalir).
    supplier: dict | None = None
    recommendation: dict | None = None

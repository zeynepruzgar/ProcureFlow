"""Uc detection kurali — saf fonksiyonlar (side-effect yok).

Girdi: basit dict listeleri (urun, stok, siparis, fiyat gecmisi).
Cikti: DetectedIssue listesi (henuz DB'ye yazilmamis "aday sinyal").

Bu ayrim kritik: kurallari DB/Supabase olmadan pytest ile test edebiliriz.
Motor (engine) sadece: veri cek → kurallari calistir → signals tablosuna yaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

# Fiyat artisi bu oranın ustundeyse "price_spike" sayilir (%20).
PRICE_SPIKE_THRESHOLD = 0.20


@dataclass(frozen=True)
class DetectedIssue:
    """Kuralların urettigi gecici sonuc. DB kaydi degil."""

    type: str  # low_stock | delayed_order | price_spike
    entity_id: str  # ilgili product / purchase_order id
    severity: str  # low | medium | high


def _as_date(value: Any) -> date | None:
    """ISO tarih / datetime / date -> date. Parse edilemezse None."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------
# 1) low_stock: stok miktari, urunun min_stock_level'inin altinda mi?
# ---------------------------------------------------------------------
def detect_low_stock(
    products: list[dict[str, Any]],
    stock_levels: list[dict[str, Any]],
) -> list[DetectedIssue]:
    """Urun + stok birlestir; quantity < min_stock_level ise sinyal uret.

    Severity:
      - quantity == 0              -> high
      - quantity < min * 0.5       -> high
      - aksi halde (yine dusuk)    -> medium
    """
    # product_id -> urun dict (hizli erisim icin harita)
    by_id = {p["id"]: p for p in products if p.get("id")}

    # Ayni urunun birden fazla lokasyonu olabilir; toplam stogu baz aliyoruz.
    totals: dict[str, float] = {}
    for row in stock_levels:
        pid = row.get("product_id")
        if not pid:
            continue
        totals[pid] = totals.get(pid, 0.0) + _as_float(row.get("quantity"))

    issues: list[DetectedIssue] = []
    for product_id, quantity in totals.items():
        product = by_id.get(product_id)
        if product is None:
            continue
        min_level = _as_float(product.get("min_stock_level"))
        if quantity >= min_level:
            continue  # sorun yok

        if quantity <= 0 or (min_level > 0 and quantity < min_level * 0.5):
            severity = "high"
        else:
            severity = "medium"

        issues.append(
            DetectedIssue(type="low_stock", entity_id=product_id, severity=severity)
        )
    return issues


# ---------------------------------------------------------------------
# 2) delayed_order: beklenen teslim tarihi gecmis ve siparis hala open
# ---------------------------------------------------------------------
def detect_delayed_orders(
    orders: list[dict[str, Any]],
    today: date | None = None,
) -> list[DetectedIssue]:
    """status == 'open' ve expected_delivery_date < today ise gecikmis.

    Severity:
      - 7 gunden fazla gecikme -> high
      - aksi halde             -> medium
    """
    today = today or date.today()
    issues: list[DetectedIssue] = []

    for order in orders:
        if order.get("status") != "open":
            continue
        expected = _as_date(order.get("expected_delivery_date"))
        if expected is None or expected >= today:
            continue

        days_late = (today - expected).days
        severity = "high" if days_late > 7 else "medium"
        order_id = order.get("id")
        if not order_id:
            continue
        issues.append(
            DetectedIssue(
                type="delayed_order", entity_id=order_id, severity=severity
            )
        )
    return issues


# ---------------------------------------------------------------------
# 3) price_spike: ayni tedarikci+urun icin son iki fiyat arasinda buyuk artis
# ---------------------------------------------------------------------
def detect_price_spikes(
    price_history: list[dict[str, Any]],
    threshold: float = PRICE_SPIKE_THRESHOLD,
) -> list[DetectedIssue]:
    """Her (supplier_id, product_id) cifti icin tarih sirali son iki fiyati karsilastir.

    Artis orani = (yeni - eski) / eski
    Oran >= threshold ise sinyal. entity_id = product_id (urun bazli takip).

    Severity:
      - artis >= %50 -> high
      - aksi halde   -> medium
    """
    # Grupla: (supplier, product) -> [(date, price), ...]
    groups: dict[tuple[str, str], list[tuple[date, float]]] = {}
    for row in price_history:
        sid = row.get("supplier_id")
        pid = row.get("product_id")
        if not sid or not pid:
            continue
        effective = _as_date(row.get("effective_date"))
        price = _as_float(row.get("unit_price"), default=-1.0)
        if effective is None or price < 0:
            continue
        groups.setdefault((sid, pid), []).append((effective, price))

    issues: list[DetectedIssue] = []
    # Ayni urun birden fazla tedarikcide spike olabilir; urun basina en agirini tut.
    best_by_product: dict[str, DetectedIssue] = {}

    for (_sid, product_id), points in groups.items():
        if len(points) < 2:
            continue
        points.sort(key=lambda item: item[0])  # eskiden yeniye
        _old_date, old_price = points[-2]
        _new_date, new_price = points[-1]
        if old_price <= 0:
            continue

        increase = (new_price - old_price) / old_price
        if increase < threshold:
            continue

        severity = "high" if increase >= 0.50 else "medium"
        candidate = DetectedIssue(
            type="price_spike", entity_id=product_id, severity=severity
        )
        existing = best_by_product.get(product_id)
        # Ayni urunde birden fazla spike varsa "high" olanı tercih et.
        if existing is None or (
            existing.severity != "high" and candidate.severity == "high"
        ):
            best_by_product[product_id] = candidate

    issues.extend(best_by_product.values())
    return issues


def run_all_rules(
    *,
    products: list[dict[str, Any]],
    stock_levels: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    price_history: list[dict[str, Any]],
    today: date | None = None,
) -> list[DetectedIssue]:
    """Uc kurali birlestirip tek liste dondurur (motor bunu cagirir)."""
    issues: list[DetectedIssue] = []
    issues.extend(detect_low_stock(products, stock_levels))
    issues.extend(detect_delayed_orders(orders, today=today))
    issues.extend(detect_price_spikes(price_history))
    return issues

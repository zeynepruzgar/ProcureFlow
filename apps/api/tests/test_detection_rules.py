"""Detection kurallarinin birim testleri — DB yok, sadece saf fonksiyonlar.

Seed verisine benzer senaryolar kullanilir:
  - A4 Paper: stok 20 < min 50  -> low_stock
  - Toner: stok 8 < min 10      -> low_stock
  - Gecikmis open siparis       -> delayed_order
  - Toner fiyati 50 -> 75 (%50) -> price_spike
"""

from datetime import date

from app.detection.rules import (
    detect_delayed_orders,
    detect_low_stock,
    detect_price_spikes,
    run_all_rules,
)

PRODUCTS = [
    {"id": "b1", "name": "A4 Paper", "min_stock_level": 50},
    {"id": "b2", "name": "Pen Box", "min_stock_level": 30},
    {"id": "b3", "name": "Toner", "min_stock_level": 10},
]

STOCK = [
    {"product_id": "b1", "quantity": 20},   # dusuk
    {"product_id": "b2", "quantity": 120},  # normal
    {"product_id": "b3", "quantity": 8},    # dusuk
]


def test_detect_low_stock_finds_items_below_minimum():
    issues = detect_low_stock(PRODUCTS, STOCK)
    entity_ids = {i.entity_id for i in issues}
    assert entity_ids == {"b1", "b3"}
    assert all(i.type == "low_stock" for i in issues)


def test_detect_low_stock_severity_high_when_far_below():
    # 20 < 50*0.5=25 -> high; 8 >= 10*0.5=5 ama 8 < 10 -> medium
    issues = {i.entity_id: i for i in detect_low_stock(PRODUCTS, STOCK)}
    assert issues["b1"].severity == "high"
    assert issues["b3"].severity == "medium"


def test_detect_low_stock_ignores_healthy_stock():
    issues = detect_low_stock(
        PRODUCTS, [{"product_id": "b2", "quantity": 120}]
    )
    assert issues == []


def test_detect_delayed_orders():
    today = date(2026, 8, 9)
    orders = [
        {
            "id": "c1",
            "status": "open",
            "expected_delivery_date": "2026-08-04",  # 5 gun gecikmis
        },
        {
            "id": "c2",
            "status": "open",
            "expected_delivery_date": "2026-08-12",  # gelecekte
        },
        {
            "id": "c3",
            "status": "received",
            "expected_delivery_date": "2026-07-01",  # teslim alindi
        },
    ]
    issues = detect_delayed_orders(orders, today=today)
    assert len(issues) == 1
    assert issues[0].entity_id == "c1"
    assert issues[0].type == "delayed_order"
    assert issues[0].severity == "medium"  # 5 gun <= 7


def test_detect_delayed_orders_high_when_very_late():
    today = date(2026, 8, 9)
    orders = [
        {
            "id": "c1",
            "status": "open",
            "expected_delivery_date": "2026-07-20",  # 20 gun gecikmis
        }
    ]
    issues = detect_delayed_orders(orders, today=today)
    assert issues[0].severity == "high"


def test_detect_price_spikes():
    history = [
        {
            "supplier_id": "a2",
            "product_id": "b3",
            "unit_price": 50.0,
            "effective_date": "2026-06-10",
        },
        {
            "supplier_id": "a2",
            "product_id": "b3",
            "unit_price": 75.0,
            "effective_date": "2026-08-07",
        },  # %50
        {
            "supplier_id": "a1",
            "product_id": "b1",
            "unit_price": 5.0,
            "effective_date": "2026-06-25",
        },
        {
            "supplier_id": "a1",
            "product_id": "b1",
            "unit_price": 5.2,
            "effective_date": "2026-08-06",
        },  # %4 — esik alti
    ]
    issues = detect_price_spikes(history)
    assert len(issues) == 1
    assert issues[0].entity_id == "b3"
    assert issues[0].type == "price_spike"
    assert issues[0].severity == "high"


def test_run_all_rules_combines_seed_like_scenarios():
    today = date(2026, 8, 9)
    issues = run_all_rules(
        products=PRODUCTS,
        stock_levels=STOCK,
        orders=[
            {
                "id": "c1",
                "status": "open",
                "expected_delivery_date": "2026-08-04",
            }
        ],
        price_history=[
            {
                "supplier_id": "a2",
                "product_id": "b3",
                "unit_price": 50.0,
                "effective_date": "2026-06-10",
            },
            {
                "supplier_id": "a2",
                "product_id": "b3",
                "unit_price": 75.0,
                "effective_date": "2026-08-07",
            },
        ],
        today=today,
    )
    types = {i.type for i in issues}
    assert types == {"low_stock", "delayed_order", "price_spike"}
    assert len([i for i in issues if i.type == "low_stock"]) == 2

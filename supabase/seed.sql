-- =====================================================================
-- ProcureFlow - Faz 1: Seed (demo) verisi
--
-- Amac: uygulamayi gercekci verilerle doldurmak ve ileride (Faz 4)
-- detection engine'in yakalayacagi UC senaryoyu onceden hazirlamak:
--   1) low_stock    -> stogu min seviyenin altinda urunler
--   2) delayed_order-> teslim tarihi gecmis, hala 'open' bir siparis
--   3) price_spike  -> tedarikci fiyatinda buyuk sicrama
--
-- Not: Bu dosya BOS/yeni bir veritabaninda calistirilmak icindir
-- (Supabase CLI'da `supabase db reset` migration'lardan sonra bunu calistirir).
-- Kolay referans icin sabit UUID'ler kullaniyoruz.
--
-- profiles (kullanicilar) burada YOK; onlar Supabase Auth ile kullanici
-- kaydolunca olusacak (Faz 2).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Tedarikciler
-- ---------------------------------------------------------------------
insert into public.suppliers (id, name, contact_email, lead_time_days, is_active) values
    ('00000000-0000-0000-0000-0000000000a1', 'Acme Supplies',  'sales@acme.example',   5,  true),
    ('00000000-0000-0000-0000-0000000000a2', 'Globex Trading', 'orders@globex.example',10, true),
    ('00000000-0000-0000-0000-0000000000a3', 'Initech Parts',  'hello@initech.example', 7, true);

-- ---------------------------------------------------------------------
-- Urunler (min_stock_level ve reorder_qty senaryolar icin onemli)
-- ---------------------------------------------------------------------
insert into public.products (id, sku, name, unit, min_stock_level, reorder_qty, preferred_supplier_id) values
    ('00000000-0000-0000-0000-0000000000b1', 'SKU-1001', 'A4 Paper Ream',      'pcs', 50, 200, '00000000-0000-0000-0000-0000000000a1'),
    ('00000000-0000-0000-0000-0000000000b2', 'SKU-1002', 'Ballpoint Pen Box',  'pcs', 30, 100, '00000000-0000-0000-0000-0000000000a1'),
    ('00000000-0000-0000-0000-0000000000b3', 'SKU-1003', 'Printer Toner',      'pcs', 10,  40, '00000000-0000-0000-0000-0000000000a2'),
    ('00000000-0000-0000-0000-0000000000b4', 'SKU-1004', 'USB-C Cable',        'pcs', 25,  80, '00000000-0000-0000-0000-0000000000a3'),
    ('00000000-0000-0000-0000-0000000000b5', 'SKU-1005', 'Desk Lamp',          'pcs', 15,  50, '00000000-0000-0000-0000-0000000000a3');

-- ---------------------------------------------------------------------
-- Stok seviyeleri
-- SENARYO 1 (low_stock): A4 Paper (20 < 50) ve Printer Toner (8 < 10) dusuk.
-- Digerleri normal.
-- ---------------------------------------------------------------------
insert into public.stock_levels (product_id, location, quantity) values
    ('00000000-0000-0000-0000-0000000000b1', 'main', 20),   -- dusuk (min 50)
    ('00000000-0000-0000-0000-0000000000b2', 'main', 120),  -- normal
    ('00000000-0000-0000-0000-0000000000b3', 'main', 8),    -- dusuk (min 10)
    ('00000000-0000-0000-0000-0000000000b4', 'main', 60),   -- normal
    ('00000000-0000-0000-0000-0000000000b5', 'main', 15);   -- normal (min ile esit)

-- ---------------------------------------------------------------------
-- Satin alma siparisleri
-- SENARYO 2 (delayed_order): po1 teslim tarihi gecmis ve hala 'open'.
-- po2 gelecekte (normal). po3 zaten teslim alinmis (sayilmaz).
-- ---------------------------------------------------------------------
insert into public.purchase_orders (id, supplier_id, status, expected_delivery_date) values
    ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000a2', 'open',     current_date - 5), -- GECIKMIS
    ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-0000000000a1', 'open',     current_date + 3), -- normal
    ('00000000-0000-0000-0000-0000000000c3', '00000000-0000-0000-0000-0000000000a3', 'received', current_date - 10); -- teslim alindi

insert into public.purchase_order_lines (po_id, product_id, qty, unit_price) values
    ('00000000-0000-0000-0000-0000000000c1', '00000000-0000-0000-0000-0000000000b3', 40, 75.0),
    ('00000000-0000-0000-0000-0000000000c2', '00000000-0000-0000-0000-0000000000b1', 200, 5.2),
    ('00000000-0000-0000-0000-0000000000c3', '00000000-0000-0000-0000-0000000000b4', 80, 3.5);

-- ---------------------------------------------------------------------
-- Fiyat gecmisi
-- SENARYO 3 (price_spike): Printer Toner (b3) fiyati Globex'te
-- 50 -> 75'e ciktı (%50 artis). Digerlerinde kucuk/normal degisim.
-- ---------------------------------------------------------------------
insert into public.supplier_price_history (supplier_id, product_id, unit_price, effective_date) values
    -- Printer Toner: eski fiyat vs yeni fiyat (buyuk sicrama)
    ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000b3', 50.0, current_date - 60),
    ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-0000000000b3', 75.0, current_date - 2),
    -- A4 Paper: kucuk normal artis
    ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000b1', 5.0, current_date - 45),
    ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-0000000000b1', 5.2, current_date - 3);

-- =====================================================================
-- ProcureFlow - Faz 1: Cekirdek veritabani semasi
-- Bu migration tum ana tablolari, aralarindaki iliskileri ve
-- sik kullanilacak indeksleri olusturur.
-- Veri modeli aciklamasi: docs/DATA_MODEL.md
-- =====================================================================

-- UUID uretimi icin gerekli eklenti (gen_random_uuid fonksiyonu).
-- Supabase'de genelde hazir gelir; garanti olsun diye ekliyoruz.
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------
-- 1) profiles: uygulama kullanicisi + rolu
--    Supabase Auth'un auth.users tablosu ile 1-1 baglidir.
--    Rol bilgisini burada tutariz (RBAC'in temeli).
-- ---------------------------------------------------------------------
create table public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    full_name text,
    -- Rol degeri check ile sinirlandirilir (ileride enum'a tasinabilir).
    role text not null default 'employee'
        check (role in (
            'employee',
            'procurement_specialist',
            'manager',
            'admin',
            'system_agent'
        )),
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 2) suppliers: tedarikciler
-- ---------------------------------------------------------------------
create table public.suppliers (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    contact_email text,
    lead_time_days int not null default 7, -- ortalama teslim suresi (gun)
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 3) products: urun katalogu + yeniden siparis parametreleri
-- ---------------------------------------------------------------------
create table public.products (
    id uuid primary key default gen_random_uuid(),
    sku text not null unique, -- urunun benzersiz kodu (stok kodu)
    name text not null,
    unit text not null default 'pcs', -- birim: adet, kg, lt...
    min_stock_level numeric not null default 0, -- altina dusunce "dusuk stok"
    reorder_qty numeric not null default 0, -- onerilecek varsayilan siparis miktari
    -- Tercih edilen tedarikci silinirse urun kalir, alan NULL olur.
    preferred_supplier_id uuid references public.suppliers (id) on delete set null,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 4) stock_levels: urun basina lokasyon bazli guncel stok
-- ---------------------------------------------------------------------
create table public.stock_levels (
    id uuid primary key default gen_random_uuid(),
    product_id uuid not null references public.products (id) on delete cascade,
    location text not null default 'main',
    quantity numeric not null default 0,
    updated_at timestamptz not null default now(),
    -- Ayni urun + ayni lokasyon icin tek satir olsun.
    unique (product_id, location)
);

-- ---------------------------------------------------------------------
-- 5) purchase_orders: acik/kapali satin alma siparisleri
--    (geciken siparis tespiti icin expected_delivery_date onemli)
-- ---------------------------------------------------------------------
create table public.purchase_orders (
    id uuid primary key default gen_random_uuid(),
    supplier_id uuid not null references public.suppliers (id),
    status text not null default 'open'
        check (status in ('open', 'received', 'cancelled')),
    expected_delivery_date date,
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 6) purchase_order_lines: siparis satirlari (bir siparis, cok urun)
-- ---------------------------------------------------------------------
create table public.purchase_order_lines (
    id uuid primary key default gen_random_uuid(),
    po_id uuid not null references public.purchase_orders (id) on delete cascade,
    product_id uuid not null references public.products (id),
    qty numeric not null,
    unit_price numeric not null
);

-- ---------------------------------------------------------------------
-- 7) supplier_price_history: tedarikci-urun fiyat gecmisi
--    (olagan disi fiyat artisi tespiti icin)
-- ---------------------------------------------------------------------
create table public.supplier_price_history (
    id uuid primary key default gen_random_uuid(),
    supplier_id uuid not null references public.suppliers (id) on delete cascade,
    product_id uuid not null references public.products (id) on delete cascade,
    unit_price numeric not null,
    effective_date date not null default current_date
);

-- ---------------------------------------------------------------------
-- 8) signals: detection engine ciktisi (tespit edilen sorunlar)
-- ---------------------------------------------------------------------
create table public.signals (
    id uuid primary key default gen_random_uuid(),
    type text not null
        check (type in ('low_stock', 'delayed_order', 'price_spike')),
    entity_id uuid not null, -- ilgili product / purchase_order / supplier kaydi
    severity text not null default 'medium'
        check (severity in ('low', 'medium', 'high')),
    status text not null default 'open'
        check (status in ('open', 'handled')),
    detected_at timestamptz not null default now()
);

-- Ayni tip + ayni varlik icin ACIK durumda tek sinyal olsun (idempotency).
-- Kismi (partial) essiz indeks: sadece status='open' satirlarina uygulanir.
create unique index uq_open_signal
    on public.signals (type, entity_id)
    where status = 'open';

-- ---------------------------------------------------------------------
-- 9) recommendations: agent'in gerekceli onerisi
-- ---------------------------------------------------------------------
create table public.recommendations (
    id uuid primary key default gen_random_uuid(),
    signal_id uuid not null references public.signals (id) on delete cascade,
    agent_run_id uuid, -- LangGraph calisma kimligi (ileride)
    rationale text, -- LLM'in urettigi gerekce metni
    suggested_supplier_id uuid references public.suppliers (id),
    suggested_qty numeric,
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'rejected')),
    reviewer_id uuid references public.profiles (id), -- onaylayan/reddeden yonetici
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 10) purchase_requests: onaylanan oneriden ureyen TASLAK talep
--     Dikkat: bu GERCEK siparis degildir. Agent yalnizca taslak uretir.
-- ---------------------------------------------------------------------
create table public.purchase_requests (
    id uuid primary key default gen_random_uuid(),
    recommendation_id uuid not null references public.recommendations (id) on delete cascade,
    supplier_id uuid references public.suppliers (id),
    lines jsonb not null default '[]'::jsonb, -- taslak satirlar (esnek yapi)
    -- Ilk surumde yalnizca 'draft' durumu var.
    status text not null default 'draft'
        check (status in ('draft')),
    created_by uuid, -- system_agent
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 11) audit_log: tum kullanici + agent islemleri (append-only / sadece ekleme)
-- ---------------------------------------------------------------------
create table public.audit_log (
    id uuid primary key default gen_random_uuid(),
    actor_id uuid, -- islemi yapan (kullanici veya agent)
    actor_type text not null default 'user'
        check (actor_type in ('user', 'agent')),
    action text not null, -- ornek: 'recommendation.approved'
    entity_table text, -- etkilenen tablo
    entity_id uuid, -- etkilenen kayit
    before jsonb, -- islem oncesi durum
    after jsonb, -- islem sonrasi durum
    created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Indeksler: sik filtrelenecek/join yapilacak alanlar icin hiz saglar.
-- ---------------------------------------------------------------------
create index idx_stock_levels_product on public.stock_levels (product_id);
create index idx_po_status on public.purchase_orders (status);
create index idx_po_lines_po on public.purchase_order_lines (po_id);
create index idx_price_history_product on public.supplier_price_history (product_id);
create index idx_signals_status on public.signals (status);
create index idx_recommendations_status on public.recommendations (status);

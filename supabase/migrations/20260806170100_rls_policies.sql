-- =====================================================================
-- ProcureFlow - Faz 1: Row Level Security (RLS) politikalari
--
-- RLS nedir? "Satir bazli guvenlik". Normalde bir tabloya erisimi olan
-- herkes tum satirlari gorur. RLS acikken ise, her satir icin
-- "bu kullanici bu satiri gorebilir/degistirebilir mi?" kurali calisir.
-- Bu, uygulama katmani atlansa bile verinin Postgres seviyesinde
-- korunmasini saglar (ikinci savunma hatti).
--
-- ONEMLI NOT: FastAPI backend'i genelde "service role" anahtariyla
-- baglanir ve service role RLS'i BYPASS eder (kurallar ona islemez).
-- Yani RLS asil su durumda devreye girer: frontend, kullanicinin kendi
-- JWT'siyle Supabase'e DOGRUDAN sorgu attiginda. Backend tarafinda
-- yetkiyi ayrica RBAC ile kod icinde uygulariz (Faz 2).
-- =====================================================================

-- ---------------------------------------------------------------------
-- Yardimci fonksiyon: o an giris yapmis kullanicinin rolunu dondurur.
-- SECURITY DEFINER onemli: fonksiyon, sahibinin yetkisiyle calisir ve
-- profiles tablosundaki RLS'e takilmadan okur. Aksi halde "profiles
-- politikasi rol icin profiles'i okur" seklinde sonsuz donguye girerdik.
-- ---------------------------------------------------------------------
create or replace function public.current_app_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
    select role from public.profiles where id = auth.uid();
$$;

-- ---------------------------------------------------------------------
-- Tum tablolarda RLS'i etkinlestir.
-- (RLS acilinca, acikca izin verilmeyen her sey VARSAYILAN OLARAK reddedilir.)
-- ---------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.suppliers enable row level security;
alter table public.products enable row level security;
alter table public.stock_levels enable row level security;
alter table public.purchase_orders enable row level security;
alter table public.purchase_order_lines enable row level security;
alter table public.supplier_price_history enable row level security;
alter table public.signals enable row level security;
alter table public.recommendations enable row level security;
alter table public.purchase_requests enable row level security;
alter table public.audit_log enable row level security;

-- =====================================================================
-- profiles
-- - Giris yapmis herkes profilleri okuyabilir (ornegin onaylayan yonetici
--   adini gostermek icin).
-- - Kullanici yalnizca kendi profilini guncelleyebilir.
-- - Admin her seyi yapabilir.
-- =====================================================================
create policy "profiles_select_all" on public.profiles
    for select to authenticated using (true);

create policy "profiles_update_self" on public.profiles
    for update to authenticated
    using (id = auth.uid())
    with check (id = auth.uid());

create policy "profiles_admin_all" on public.profiles
    for all to authenticated
    using (public.current_app_role() = 'admin')
    with check (public.current_app_role() = 'admin');

-- =====================================================================
-- Referans / is verisi tablolari
-- Desen: giris yapmis herkes OKUR; yalnizca yetkili roller YAZAR.
-- Yetkili yazar roller: procurement_specialist, manager, admin.
-- Tablolar: suppliers, products, stock_levels, purchase_orders,
--           purchase_order_lines, supplier_price_history
-- =====================================================================

-- suppliers
create policy "suppliers_select" on public.suppliers
    for select to authenticated using (true);
create policy "suppliers_write" on public.suppliers
    for all to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'))
    with check (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- products
create policy "products_select" on public.products
    for select to authenticated using (true);
create policy "products_write" on public.products
    for all to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'))
    with check (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- stock_levels
create policy "stock_levels_select" on public.stock_levels
    for select to authenticated using (true);
create policy "stock_levels_write" on public.stock_levels
    for all to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'))
    with check (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- purchase_orders
create policy "purchase_orders_select" on public.purchase_orders
    for select to authenticated using (true);
create policy "purchase_orders_write" on public.purchase_orders
    for all to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'))
    with check (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- purchase_order_lines
create policy "purchase_order_lines_select" on public.purchase_order_lines
    for select to authenticated using (true);
create policy "purchase_order_lines_write" on public.purchase_order_lines
    for all to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'))
    with check (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- supplier_price_history
create policy "supplier_price_history_select" on public.supplier_price_history
    for select to authenticated using (true);
create policy "supplier_price_history_write" on public.supplier_price_history
    for all to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'))
    with check (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- =====================================================================
-- signals: detection engine ciktisi
-- - Giris yapmis herkes okuyabilir (dashboard'da listelemek icin).
-- - Yazma islemi normalde backend/service role uzerinden olur; burada
--   ek olarak yetkili rollere de izin veriyoruz.
-- =====================================================================
create policy "signals_select" on public.signals
    for select to authenticated using (true);
create policy "signals_write" on public.signals
    for all to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'))
    with check (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- =====================================================================
-- recommendations: agent onerileri
-- - Giris yapmis herkes okuyabilir.
-- - Onaylama/reddetme (update) yalnizca manager ve admin.
--   (Oneriyi olusturan agent, backend'de service role ile insert eder.)
-- =====================================================================
create policy "recommendations_select" on public.recommendations
    for select to authenticated using (true);
create policy "recommendations_review" on public.recommendations
    for update to authenticated
    using (public.current_app_role() in ('manager', 'admin'))
    with check (public.current_app_role() in ('manager', 'admin'));

-- =====================================================================
-- purchase_requests: taslak satin alma talepleri
-- - Yalnizca yetkili roller gorur.
--   (Olusturma agent tarafindan service role ile yapilir.)
-- =====================================================================
create policy "purchase_requests_select" on public.purchase_requests
    for select to authenticated
    using (public.current_app_role() in ('procurement_specialist', 'manager', 'admin'));

-- =====================================================================
-- audit_log: append-only (sadece ekleme) izlenebilirlik kaydi
-- - Yalnizca manager ve admin okuyabilir.
-- - UPDATE/DELETE icin hicbir politika YOK => varsayilan olarak yasak.
--   Boylece gecmis kayitlar degistirilemez.
-- =====================================================================
create policy "audit_log_select" on public.audit_log
    for select to authenticated
    using (public.current_app_role() in ('manager', 'admin'));

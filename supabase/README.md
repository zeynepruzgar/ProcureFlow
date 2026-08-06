# Supabase

Database schema, Row Level Security (RLS) policies, and seed data for ProcureFlow.

Data model: [../docs/DATA_MODEL.md](../docs/DATA_MODEL.md)

## Layout

```text
supabase/
  migrations/
    20260806170000_core_schema.sql      # tablolar + iliskiler + indeksler
    20260806170100_rls_policies.sql     # RLS (satir bazli guvenlik)
    20260806180000_profiles_trigger.sql # yeni kullanicida otomatik profil (Faz 2)
  seed.sql                              # demo veri (3 senaryoyu hazirlar)
```

## Uygulama (iki yol)

### Yol A - Supabase Dashboard (en kolay, ilk kez icin onerilen)

1. [supabase.com](https://supabase.com) uzerinde ucretsiz bir proje olustur.
2. Sol menuden **SQL Editor**'u ac.
3. Sirasiyla su dosyalarin icerigini yapistirip **Run** de:
   1. `migrations/20260806170000_core_schema.sql`
   2. `migrations/20260806170100_rls_policies.sql`
   3. `migrations/20260806180000_profiles_trigger.sql`
   4. `seed.sql`
4. **Table Editor**'den tablolarin ve verilerin geldigini kontrol et.
5. Proje ayarlarindan `Project URL` ve `anon` / `service_role` anahtarlarini
   alip kok `.env` dosyana yaz (bkz. `.env.example`).

### Yol B - Supabase CLI (profesyonel migration akisi)

```bash
# CLI kurulumu (macOS)
brew install supabase/tap/supabase

# Projeye baglan (proje ref'ini dashboard'dan al)
supabase link --project-ref YOUR_PROJECT_REF

# Migration'lari uzak veritabanina uygula
supabase db push

# (Alternatif) Yerel gelistirme veritabanini sifirla + migration + seed
# Not: yerel mod Docker gerektirir.
supabase db reset
```

## Notlar

- Auth (giris) Supabase Auth ile yapilir; uygulama rolleri `profiles.role`'da tutulur.
- Her tabloda RLS aciktir. Backend `service_role` anahtariyla baglaninca RLS'i
  bypass eder; bu yuzden backend kendi RBAC kontrolunu de uygular (Faz 2).
- `profiles` satirlari kullanicilar kaydolunca `on_auth_user_created` trigger'i ile
  otomatik olusur (Faz 2). Seed yalnizca is verisini (urun, tedarikci, stok, siparis,
  fiyat) doldurur.
- Kolay test icin: Supabase Dashboard -> Authentication -> Sign In / Providers ->
  Email bolumunde "Confirm email" secenegini gelistirme sirasinda kapatabilirsin;
  boylece kaydolur kaydolmaz giris yapabilirsin.
- Ilk admin kullanicin: kaydol, sonra SQL Editor'de rolunu yukselt:
  `update public.profiles set role = 'admin' where id = (select id from auth.users where email = 'SENIN_EPOSTAN');`

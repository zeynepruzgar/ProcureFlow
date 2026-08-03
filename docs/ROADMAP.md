# ProcureFlow — Yol Haritası

Fazlı geliştirme planı. Her faz kendi başına gösterilebilir bir çıktı üretir. Fazlar birbirinin üzerine kurulur.

Referanslar: [ARCHITECTURE.md](./ARCHITECTURE.md) · [DATA_MODEL.md](./DATA_MODEL.md) · [AGENT.md](./AGENT.md)

---

## Faz 0 — Monorepo İskeleti
**Amaç:** Çalışan bir temel ve tutarlı geliştirme deneyimi.
- `apps/web` (Next.js + TS + Tailwind + shadcn/ui) boş ama çalışır kurulum.
- `apps/api` (FastAPI + Pydantic) sağlık kontrolü (`/health`) endpoint'i.
- `supabase/`, `docs/`, `docker/`, `.github/` klasörleri.
- Env konvansiyonları (`.env.example`), README, lint/format ayarları, temel CI.
- **Çıktı:** `docker-compose up` ile web + api + (Ollama) lokal ayağa kalkar.

## Faz 1 — Veritabanı Şeması + RLS + Seed
**Amaç:** Tüm çekirdek tablolar ve güvenlik zemini.
- `supabase/` altında migration'lar: DATA_MODEL.md'deki tüm tablolar.
- RLS politikaları ve roller (`profiles.role`).
- Seed data: örnek ürünler, tedarikçiler, stok, açık siparişler, fiyat geçmişi.
- **Çıktı:** Gerçekçi demo verisiyle dolu, RLS korumalı bir veritabanı.

## Faz 2 — Auth + RBAC
**Amaç:** Giriş ve rol bazlı erişim.
- Supabase Auth entegrasyonu (web login/logout, oturum).
- API'de JWT doğrulama + rol bazlı bağımlılıklar.
- `profiles` otomatik oluşturma (yeni kullanıcı → profil + varsayılan rol).
- **Çıktı:** Farklı rollerle giriş yapıldığında farklı yetkiler.

## Faz 3 — Çekirdek CRUD + Dashboard
**Amaç:** Görünür ürün.
- Ürün, stok, sipariş, tedarikçi listeleme/detay ekranları (shadcn/ui).
- API CRUD endpoint'leri + Pydantic şemaları.
- Ana dashboard iskeleti (kartlar, tablolar).
- **Çıktı:** Verinin gezilebildiği gerçek bir dashboard.

## Faz 4 — Detection Engine
**Amaç:** Otomatik sorun tespiti.
- 3 kural: `low_stock`, `delayed_order`, `price_spike`.
- Zamanlanmış job (APScheduler/platform cron) + manuel `POST /scan`.
- Idempotent `signals` üretimi + dashboard'da sinyal listesi.
- **Çıktı:** Sistem sorunları kendi tespit edip listeliyor.

## Faz 5 — LangGraph Agent
**Amaç:** Gerekçeli öneri üretimi.
- Read-only araçlar (get_product, get_stock, get_open_orders, ...).
- LangGraph grafiği: gather_context → analyze → write_recommendation.
- Sağlayıcı-bağımsız LLM (`get_chat_model`), Ollama ile başla.
- **Çıktı:** Bir sinyalden `pending` gerekçeli öneri üretiliyor.

## Faz 6 — Onay İş Akışı → Taslak Talep
**Amaç:** Human-in-the-loop.
- LangGraph `interrupt` + Postgres checkpointer.
- Web'de öneri detay + onayla/reddet.
- Onayda `purchase_requests (draft)` oluşturma.
- **Çıktı:** Yönetici onaylayınca taslak satın alma talebi oluşuyor.

## Faz 7 — Audit Log
**Amaç:** İzlenebilirlik.
- Tüm kullanıcı + agent işlemleri `audit_log`'a (append-only).
- Web'de audit görünümü (manager/admin).
- **Çıktı:** Her işlemin kim/ne/ne zaman kaydı görülebiliyor.

## Faz 8 — Test + Docker + Deployment
**Amaç:** Production'a hazır.
- Pytest (detection, tools, grafik — LLM mock), Vitest (web), Playwright (e2e).
- Dockerfile'lar + CI'da test.
- Vercel (web) + Render/Railway (api) deploy; hosted LLM'e geçiş dokümanı.
- **Çıktı:** Canlı, test edilmiş, gösterilebilir bir uygulama.

---

## Öneri Sırası ve İlke

- Fazları sırayla ilerlet; her fazın sonunda commit + kısa demo notu.
- İlk uçtan uca dikey dilim: **düşük stok → agent önerisi → onay → taslak
  talep → audit**. Bu tamamlandığında proje "anlatılabilir" hale gelir; diğer
  iki sinyal tipi aynı boru hattına eklenir.

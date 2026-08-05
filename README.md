# ProcureFlow — Agentic Procurement & Inventory Operations

Bir işletmenin **stok ve satın alma** süreçlerini yöneten ERP modülü. Sistem
düşük stok, geciken sipariş ve olağan dışı fiyat artışlarını tespit eder; bir
**AI agent** ürün, stok, açık sipariş ve tedarikçi verilerini araçlar üzerinden
inceleyip **gerekçeli satın alma önerisi** hazırlar ve yönetici onayına gönderir.

## Teknolojiler

- **Frontend:** Next.js, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** Python, FastAPI, Pydantic
- **Agent:** LangGraph (geliştirme Ollama, production GPT-5 nano)
- **Database/Auth:** Supabase PostgreSQL + Supabase Auth
- **Authorization:** RBAC + Row Level Security
- **Test:** Pytest, Vitest, Playwright
- **Deployment:** Vercel (web), Render/Railway (api), Docker

## Roller

Employee · Procurement Specialist · Manager · Admin · System Agent

## Depo Yapısı

```text
apps/web     # Next.js dashboard
apps/api     # FastAPI + LangGraph agent + detection
supabase     # şema, RLS, seed
docs         # mimari ve tasarım dokümanları
docker       # yerel orkestrasyon notları
```

## Hızlı Başlangıç

Ortam değişkenleri için `.env.example` dosyalarını kopyalayın (kök, `apps/api`, `apps/web`).

API (Python 3.12):

```bash
cd apps/api
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000  (docs: /docs)
```

Web (Node 22):

```bash
cd apps/web
npm install
npm run dev                     # http://localhost:3000
```

Docker ile hepsi birden (web + api + ollama):

```bash
docker compose up --build
```

## Dokümantasyon

- [Mimari](./docs/ARCHITECTURE.md)
- [Veri Modeli](./docs/DATA_MODEL.md)
- [Agent Tasarımı](./docs/AGENT.md)
- [Yol Haritası](./docs/ROADMAP.md)

## Durum

Aktif geliştirme. Faz sırası için bkz. [ROADMAP.md](./docs/ROADMAP.md).

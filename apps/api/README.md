# ProcureFlow API

FastAPI backend for ProcureFlow (detection engine + LangGraph agent + REST API).

## Local development

Requires Python 3.12 (pinned in `.python-version`; some deps lack 3.14 wheels).

```bash
cd apps/api
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Tests & lint

```bash
pytest
ruff check .
```

## Loglama

Seviye `.env` icindeki `LOG_LEVEL` ile ayarlanir (varsayilan `INFO`).
Kurulum: `app/core/logging.py`.

- `INFO` — agent akisinin her adimi: hangi baglam toplandi, LLM'e hangi model
  ile gidildi, **LLM'in ham cevabi**, hangi oneri/taslak talep yazildi.
- `DEBUG` — ek olarak LLM'e giden **tam prompt** ve toplanan tam baglam.
- LLM cagrisi basarisiz olursa `WARNING` + traceback basilir ve akis kural
  tabanli sablona duser. "Neden gerekce sablondan geldi?" sorusunun cevabi
  bu satirdadir (ornegin `ConnectError: [Errno 61] Connection refused`
  → Ollama ayakta degil).

Tek bir agent calismasini takip etmek icin log satirlarindaki `[run <id>]`
onekini kullanin: onay akisi iki ayri HTTP istegine (`/recommend` ve
`/approve`) yayildigi icin ayni `run_id` her ikisinde de gorunur.

```bash
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

## Structure

```text
app/
  core/      # config, settings, shared deps
  main.py    # FastAPI app + health endpoint
tests/       # pytest
```

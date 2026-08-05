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

## Structure

```text
app/
  core/      # config, settings, shared deps
  main.py    # FastAPI app + health endpoint
tests/       # pytest
```

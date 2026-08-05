# Docker

Local orchestration for ProcureFlow. The compose file lives at the repo root
(`docker-compose.yml`) and wires three services:

- `web` &mdash; Next.js app on http://localhost:3000
- `api` &mdash; FastAPI app on http://localhost:8000
- `ollama` &mdash; local LLM provider on http://localhost:11434

## Usage

```bash
# from repo root
docker compose up --build
```

First run, pull a model into Ollama (in another terminal):

```bash
docker compose exec ollama ollama pull llama3.1
```

## Notes

- Per-service Dockerfiles live in `apps/api/Dockerfile` and `apps/web/Dockerfile`.
- To use a hosted LLM instead of Ollama, set `LLM_PROVIDER`/`LLM_MODEL` and the
  provider API key on the `api` service (see `.env.example`).

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="ProcureFlow API",
    description="Agentic Procurement & Inventory Operations API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness/readiness probe."""
    return HealthResponse(status="ok", service="procureflow-api", version=app.version)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"message": "ProcureFlow API. See /docs for the OpenAPI UI."}

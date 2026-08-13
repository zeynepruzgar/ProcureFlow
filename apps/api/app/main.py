from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import get_settings
from app.routers import auth as auth_router
from app.routers import inventory as inventory_router
from app.routers import orders as orders_router
from app.routers import products as products_router
from app.routers import recommendations as recommendations_router
from app.routers import signals as signals_router
from app.routers import suppliers as suppliers_router

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


# Rota gruplarini (router) uygulamaya bagla.
app.include_router(auth_router.router)
app.include_router(products_router.router)
app.include_router(suppliers_router.router)
app.include_router(inventory_router.router)
app.include_router(orders_router.router)
app.include_router(signals_router.router)
app.include_router(recommendations_router.router)

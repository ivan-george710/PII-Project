from fastapi import FastAPI

from app.routes.health import router as health_router

app = FastAPI(
    title="PII Guard API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
app.include_router(health_router)

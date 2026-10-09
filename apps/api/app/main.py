from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import register_feature_routers
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.organization import router as organization_router
from app.schemas.common import ApiError, error_body

app = FastAPI(
    title="PII Guard API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)
for router in (health_router, auth_router, organization_router):
    app.include_router(router)
register_feature_routers(app)


@app.exception_handler(ApiError)
async def api_error(request: Request, error: ApiError):
    return JSONResponse(
        error_body(error.code, error.message, error.fields),
        status_code=error.status,
        headers={"Cache-Control": "no-store"},
    )


@app.exception_handler(RequestValidationError)
async def invalid(request: Request, error: RequestValidationError):
    fields = [
        {"path": ".".join(str(p) for p in e["loc"][1:]), "message": "Invalid value"}
        for e in error.errors()
    ]
    return JSONResponse(
        error_body("VALIDATION_ERROR", "Invalid request", fields), status_code=422
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    return JSONResponse(
        error_body("DATABASE_UNAVAILABLE", "Company data is unavailable"),
        status_code=503,
    )


@app.middleware("http")
async def private_api(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response.headers["Cache-Control"] = "no-store"
    return response

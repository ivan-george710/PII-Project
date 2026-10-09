from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

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

# Core and implemented feature routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(organization_router)

# Feature routers from Issue 2 (Employee Chat, Uploads, Demo Samples)
try:
    from app.routes.chat import router as chat_router  # type: ignore

    app.include_router(chat_router)
except ImportError:
    # TODO: Issue #2 - Employee chat router (apps/api/app/routes/chat.py)
    pass

try:
    from app.routes.uploads import router as uploads_router  # type: ignore

    app.include_router(uploads_router)
except ImportError:
    # TODO: Issue #2 - Uploads router (apps/api/app/routes/uploads.py)
    pass

try:
    from app.routes.demo import router as demo_router  # type: ignore

    app.include_router(demo_router)
except ImportError:
    # TODO: Issue #2 - Demo samples router (apps/api/app/routes/demo.py)
    pass

# Feature routers from Issue 4 (Manager Rules and Reports)
try:
    from app.routes.rules import router as rules_router  # type: ignore

    app.include_router(rules_router)
except ImportError:
    # TODO: Issue #4 - Manager rules router (apps/api/app/routes/rules.py)
    pass

try:
    from app.routes.reports import router as reports_router  # type: ignore

    app.include_router(reports_router)
except ImportError:
    # TODO: Issue #4 - Manager reports router (apps/api/app/routes/reports.py)
    pass


@app.exception_handler(ApiError)
async def api_error(request: Request, error: ApiError):
    return JSONResponse(
        error_body(error.code, error.message, error.fields if hasattr(error, "fields") else None),
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

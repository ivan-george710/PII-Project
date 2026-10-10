import os

from fastapi import APIRouter, Response

from app.schemas.common import HealthResponse, ApiError

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    response.headers["Cache-Control"] = "no-store"
    if (
        os.getenv("APP_ENV", "production" if os.getenv("VERCEL") else "development")
        == "production"
    ):
        # A deployed API is usable only if its packaged privacy models initialize.
        # CI calls this endpoint before accepting/promoting the deployment.
        from app.services.engine_adapter import privacy_engine

        try:
            privacy_engine()
        except Exception:
            raise ApiError(
                503, "GUARD_UNAVAILABLE", "Required privacy models are unavailable"
            ) from None
    return HealthResponse(commit=os.getenv("VERCEL_GIT_COMMIT_SHA"))

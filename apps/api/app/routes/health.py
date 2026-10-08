import os

from fastapi import APIRouter, Response

from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    response.headers["Cache-Control"] = "no-store"
    return HealthResponse(commit=os.getenv("VERCEL_GIT_COMMIT_SHA"))

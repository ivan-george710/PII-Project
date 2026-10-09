from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_manager
from app.schemas.reports import ReportEvent, ReportEventsPage, ReportSummaryResponse
from app.services.reporting import get_event_detail, get_reports, get_summary

router = APIRouter(prefix="/api/v1/reports", tags=["Manager reports"])


@router.get("", response_model=ReportEventsPage)
def get_reports_endpoint(
    employee_id: UUID | None = Query(None),
    category: str | None = Query(None, min_length=1, max_length=80),
    action: str | None = Query(None),
    from_time: datetime | None = Query(None),
    to_time: datetime | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return get_reports(
        db=db,
        organization_id=identity.organization_id,
        manager_id=identity.user_id,
        employee_id=employee_id,
        category=category,
        action=action,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        cursor=cursor,
    )


@router.get("/summary", response_model=ReportSummaryResponse)
def get_reports_summary_endpoint(
    employee_id: UUID | None = Query(None),
    category: str | None = Query(None, min_length=1, max_length=80),
    action: str | None = Query(None),
    from_time: datetime | None = Query(None),
    to_time: datetime | None = Query(None),
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return get_summary(
        db=db,
        organization_id=identity.organization_id,
        manager_id=identity.user_id,
        employee_id=employee_id,
        category=category,
        action=action,
        from_time=from_time,
        to_time=to_time,
    )


@router.get("/{event_id}", response_model=ReportEvent)
def get_report_event_detail_endpoint(
    event_id: UUID,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return get_event_detail(
        db=db,
        organization_id=identity.organization_id,
        manager_id=identity.user_id,
        event_id=event_id,
    )

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models.manager_assignment import ManagerAssignment
from app.db.models.pii_event import PiiEvent
from app.db.models.user import User
from app.schemas.common import ApiError
from app.schemas.reports import (
    EmployeeSummary,
    EventBatch,
    GroupedFinding,
    ReportCategoryCount,
    ReportEvent,
    ReportEventsPage,
    ReportSummaryResponse,
    SourceLocation,
)


def record(db: Session, batch: EventBatch) -> None:
    """Internal idempotent event batch ingestion."""
    existing = (
        db.query(PiiEvent)
        .filter(
            PiiEvent.company_id == batch.organization_id,
            PiiEvent.submission_id == batch.submission_id,
            PiiEvent.policy_version == batch.policy_version,
        )
        .first()
    )
    if existing is not None:
        # Check if identical (no-op replay) or conflict
        if (
            str(existing.employee_id) != str(batch.employee_id)
            or existing.status != batch.status
            or existing.failure_code != batch.failure_code
        ):
            raise ApiError(409, "CONFLICT", "Conflicting event batch submission")
        return

    findings_json = [f.model_dump(mode="json") for f in batch.findings]
    event = PiiEvent(
        company_id=batch.organization_id,
        submission_id=batch.submission_id,
        employee_id=batch.employee_id,
        policy_version=batch.policy_version,
        occurred_at=batch.occurred_at,
        status=batch.status,
        failure_code=batch.failure_code,
        findings=findings_json,
    )
    db.add(event)
    db.commit()


def get_assigned_employee_ids(db: Session, organization_id: UUID, manager_id: UUID) -> set[UUID]:
    rows = (
        db.query(ManagerAssignment.employee_id)
        .filter(
            ManagerAssignment.organization_id == organization_id,
            ManagerAssignment.manager_id == manager_id,
        )
        .all()
    )
    return {r[0] for r in rows}


def _group_findings(raw_findings: list) -> list[GroupedFinding]:
    """Group identical (rule_id, category, action) findings while preserving locations."""
    groups: dict[tuple[str, str, str], list[SourceLocation]] = defaultdict(list)
    for f in raw_findings:
        key = (f["rule_id"], f["category"], f["action"])
        loc = SourceLocation.model_validate(f["location"])
        groups[key].append(loc)

    result = []
    for (rule_id, category, action), locations in groups.items():
        result.append(
            GroupedFinding(
                rule_id=rule_id,
                category=category,
                count=len(locations),
                action=action,  # type: ignore
                locations=locations,
            )
        )
    return result


def _to_report_event(event: PiiEvent, employee: User) -> ReportEvent:
    grouped = _group_findings(event.findings or [])
    total_findings = sum(g.count for g in grouped)
    return ReportEvent(
        id=event.id,
        submission_id=event.submission_id,
        employee=EmployeeSummary(
            id=employee.id,
            display_name=employee.display_name,
            email=employee.email,
        ),
        occurred_at=event.occurred_at,
        policy_version=event.policy_version,
        status=event.status,  # type: ignore
        failure_code=event.failure_code,
        findings=grouped,
        total_findings=total_findings,
    )


def get_reports(
    db: Session,
    organization_id: UUID,
    manager_id: UUID,
    employee_id: UUID | None = None,
    category: str | None = None,
    action: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = 25,
    cursor: str | None = None,
) -> ReportEventsPage:
    if from_time and to_time and from_time > to_time:
        raise ApiError(422, "INVALID_DATE_RANGE", "from_time must be less than or equal to to_time")

    assigned_ids = get_assigned_employee_ids(db, organization_id, manager_id)
    if employee_id is not None:
        if employee_id not in assigned_ids:
            # Querying unassigned employee yields empty list, not error
            return ReportEventsPage(items=[], next_cursor=None)
        allowed_ids = {employee_id}
    else:
        allowed_ids = assigned_ids

    if not allowed_ids:
        return ReportEventsPage(items=[], next_cursor=None)

    query = (
        db.query(PiiEvent, User)
        .join(User, PiiEvent.employee_id == User.id)
        .filter(
            PiiEvent.company_id == organization_id,
            PiiEvent.employee_id.in_(allowed_ids),
        )
    )

    if from_time is not None:
        query = query.filter(PiiEvent.occurred_at >= from_time)
    if to_time is not None:
        query = query.filter(PiiEvent.occurred_at <= to_time)

    # Order by occurred_at descending, then id descending
    query = query.order_by(desc(PiiEvent.occurred_at), desc(PiiEvent.id))

    # Apply cursor pagination if present (cursor format: ISO_TIMESTAMP|UUID)
    if cursor:
        try:
            cur_time_str, cur_id_str = cursor.split("|")
            cur_time = datetime.fromisoformat(cur_time_str)
            cur_id = UUID(cur_id_str)
            query = query.filter(
                (PiiEvent.occurred_at < cur_time)
                | ((PiiEvent.occurred_at == cur_time) & (PiiEvent.id < cur_id))
            )
        except Exception:
            raise ApiError(422, "INVALID_CURSOR", "Invalid pagination cursor")

    # Fetch limit + 1 to determine next cursor
    fetch_limit = min(max(1, limit), 100)
    records = query.limit(fetch_limit + 1).all()

    items: list[ReportEvent] = []
    for event, user in records[:fetch_limit]:
        report_evt = _to_report_event(event, user)
        # Apply finding-level category and action filter if specified
        if category or action:
            filtered_findings = [
                f
                for f in report_evt.findings
                if (not category or f.category.lower() == category.lower() or f.rule_id.lower() == category.lower())
                and (not action or f.action == action)
            ]
            if not filtered_findings:
                continue
            report_evt.findings = filtered_findings
            report_evt.total_findings = sum(f.count for f in filtered_findings)
        items.append(report_evt)

    next_cursor = None
    if len(records) > fetch_limit:
        last_evt = records[fetch_limit - 1][0]
        next_cursor = f"{last_evt.occurred_at.isoformat()}|{str(last_evt.id)}"

    return ReportEventsPage(items=items, next_cursor=next_cursor)


def get_summary(
    db: Session,
    organization_id: UUID,
    manager_id: UUID,
    employee_id: UUID | None = None,
    category: str | None = None,
    action: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> ReportSummaryResponse:
    if from_time and to_time and from_time > to_time:
        raise ApiError(422, "INVALID_DATE_RANGE", "from_time must be less than or equal to to_time")

    assigned_ids = get_assigned_employee_ids(db, organization_id, manager_id)
    if employee_id is not None:
        if employee_id not in assigned_ids:
            return ReportSummaryResponse(
                submission_count=0,
                failed_count=0,
                redacted_count=0,
                allowed_disabled_count=0,
                by_category=[],
            )
        allowed_ids = {employee_id}
    else:
        allowed_ids = assigned_ids

    if not allowed_ids:
        return ReportSummaryResponse(
            submission_count=0,
            failed_count=0,
            redacted_count=0,
            allowed_disabled_count=0,
            by_category=[],
        )

    query = db.query(PiiEvent).filter(
        PiiEvent.company_id == organization_id,
        PiiEvent.employee_id.in_(allowed_ids),
    )
    if from_time is not None:
        query = query.filter(PiiEvent.occurred_at >= from_time)
    if to_time is not None:
        query = query.filter(PiiEvent.occurred_at <= to_time)

    events = query.all()

    submission_count = len(events)
    failed_count = sum(1 for e in events if e.status == "failed")
    redacted_count = 0
    allowed_disabled_count = 0
    cat_counts: dict[str, int] = defaultdict(int)

    for e in events:
        for f in e.findings or []:
            f_cat = f.get("category", "General")
            f_act = f.get("action")
            f_rule = f.get("rule_id")
            if category and category.lower() not in (f_cat.lower(), str(f_rule).lower()):
                continue
            if action and action != f_act:
                continue

            if f_act == "redacted":
                redacted_count += 1
            elif f_act == "allowed_disabled":
                allowed_disabled_count += 1
            cat_counts[f_cat] += 1

    by_category = [
        ReportCategoryCount(category=k, count=v) for k, v in sorted(cat_counts.items())
    ]
    return ReportSummaryResponse(
        submission_count=submission_count,
        failed_count=failed_count,
        redacted_count=redacted_count,
        allowed_disabled_count=allowed_disabled_count,
        by_category=by_category,
    )


def get_event_detail(
    db: Session, organization_id: UUID, manager_id: UUID, event_id: UUID
) -> ReportEvent:
    assigned_ids = get_assigned_employee_ids(db, organization_id, manager_id)
    row = (
        db.query(PiiEvent, User)
        .join(User, PiiEvent.employee_id == User.id)
        .filter(
            PiiEvent.id == event_id,
            PiiEvent.company_id == organization_id,
        )
        .first()
    )
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Event not found")

    event, user = row
    if event.employee_id not in assigned_ids:
        # Unassigned employee events are protected and return 404
        raise ApiError(404, "NOT_FOUND", "Event not found")

    return _to_report_event(event, user)

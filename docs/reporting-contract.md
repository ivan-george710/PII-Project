# Reporting Contract Specification

This document defines the contract for internal PII event ingestion, idempotency guarantees, and manager-facing audit reports.

## Core Privacy Principle
**Audit logs never persist or display raw matched PII.**
Reports record metadata only: rule ID, category, match count, location coordinates, action taken (`redacted` vs `allowed_disabled`), employee identity, and timestamp.

---

## Internal Event Ingestion (`EventBatch`)

Internal event recording is a service interface: `record(event_batch: EventBatch) -> None`.

### Ingestion Contract
```json
{
  "submission_id": "UUID",
  "organization_id": "UUID",
  "employee_id": "UUID",
  "policy_version": 1,
  "occurred_at": "2026-10-10T00:00:00Z",
  "status": "completed",
  "failure_code": null,
  "findings": [
    {
      "id": "UUID",
      "rule_id": "CREDIT_CARD",
      "category": "Financial",
      "confidence": 0.95,
      "recognizer": "regex",
      "location": {
        "artifact_id": null,
        "kind": "message",
        "page_number": null,
        "slide_number": null,
        "source_ref": null,
        "start": 12,
        "end": 28,
        "bbox": null
      },
      "action": "redacted"
    }
  ]
}
```

### Idempotency Rules
1. Uniqueness is enforced on `(organization_id, submission_id, policy_version)`.
2. **Identical Replays**: Re-recording an identical event batch is treated as a safe no-op (idempotent success).
3. **Conflicting Replays**: Re-recording a batch with matching key but different data yields an error (`409 Conflict`).
4. Submissions where zero PII was detected are still durably recorded with empty `findings: []` to preserve full submission audit logs.
5. If `status == "failed"`, `failure_code` is required.

---

## Manager Public Reporting Model (`ReportEvent`)

### Schema
```json
{
  "id": "UUID",
  "submission_id": "UUID",
  "employee": {
    "id": "UUID",
    "display_name": "Alice Smith",
    "email": "alice@company.com"
  },
  "occurred_at": "2026-10-10T00:00:00Z",
  "policy_version": 1,
  "status": "completed",
  "failure_code": null,
  "findings": [
    {
      "rule_id": "CREDIT_CARD",
      "category": "Financial",
      "count": 1,
      "action": "redacted",
      "locations": [
        {
          "artifact_id": null,
          "kind": "message",
          "page_number": null,
          "slide_number": null,
          "source_ref": null,
          "start": 12,
          "end": 28,
          "bbox": null
        }
      ]
    }
  ],
  "total_findings": 1
}
```

### Authorization & Scoping
1. **Company Isolation**: Managers can only query events originating from their own organization.
2. **Assigned-Employee Scoping**: Managers can only view reports for employees actively assigned to them via `ManagerAssignment`.
3. Direct lookups (`GET /api/v1/reports/{event_id}`) for an event from an unassigned employee or foreign organization return `404 Not Found`.

### Query Filters
- `from_time` & `to_time`: RFC3339 UTC timestamps (`from_time <= to_time`).
- `employee_id`: UUID string.
- `category`: Category name string (1..80 chars).
- `action`: `"redacted"` or `"allowed_disabled"`.

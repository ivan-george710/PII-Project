**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Deliver manager rule settings, custom rules, and employee PII reporting

Status: Approved for implementation and GitHub publication.
Suggested ownership: Full-stack manager settings / reporting

Implement the entire manager workflow: company-wide rule controls, custom rules, persisted events, and assigned-employee reports, with frontend, backend, migrations, validation, and feature checks together. Consume the documented SessionIdentity/assignment interface; do not wait for an authentication issue to close.

## Scope

- Company built-in toggles, all-on/all-off, custom phrase/regex editing/preview, and immutable versioned policy snapshots.
- Idempotent internal PII event ingestion and assigned-employee-only reports with category/date/action filters.
- Manager settings and report screens inside the plain app shell.
- Database models/migration, safe public DTOs, error handling, optimistic concurrency, and scoped access.
- Synthetic policy/event adapters and feature checks are part of this issue, not a separate testing/demo task.

## Acceptance criteria

- All13 built-in rules default on; custom rules validate, preview, save, and obey version conflicts.
- Enabled matches are redacted; disabled matches remain visible in reports as allowed_disabled.
- Reports contain rule/category/count/location/action/employee/time, without raw matched PII.
- Managers see only currently assigned employees in their own company, including direct-resource requests.
- Replayed event batches do not duplicate reports; conflicting duplicates fail safely.
- Pydantic/Zod enforce every exact request/response contract and invalid-pattern/time-limit cases.

## Mandatory validation and shared conventions

Use **Pydantic v2** for Python request/response models, engine contracts, stored JSON policies/events, and provider-bound requests. Use **Zod** for frontend forms, REST responses, and streaming event payloads; TypeScript types alone are not runtime validation. Add `apps/web/src/lib/schemas.ts` for Zod schemas. Use FastAPI’s generated OpenAPI and check matching frontend payloads within this feature’s tests.

- Base Python schema: `BaseModel` with `ConfigDict(extra="forbid", validate_assignment=True)`. Use `StrictBool`, `StrictInt`, constrained strings/lists, enums, UUID, and timezone-aware datetime fields. Do not coerce strings such as `"false"` into booleans. Parse legitimate UUID/date strings deliberately at the transport boundary. Do not use `model_construct()` for external data. Use `model_validate`/`model_validate_json` on integrations and `model_dump(mode="json")` for serialization.
- Frontend: strict Zod objects, matching bounds/enums, `.safeParse()` with field feedback for forms, `.parse()`/`.safeParse()` for every API/SSE response. Malformed responses are errors, not a successful operation. Python validation remains authoritative.
- REST prefix `/api/v1`; health stays `/api/health`. Field names use snake_case. IDs are UUID strings; timestamps are RFC3339 UTC (`Z`). Organization and acting-user IDs always come from the validated session, never a client claim.
- JSON error shape: `{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","fields":[{"path":"text","message":"Too long"}],"request_id":"<uuid>"}}`. Never include original PII, secrets, tracebacks, or rejected raw field values. Use 401 unauthenticated, 403 wrong role, 404 unavailable/foreign resource, 409 conflict, 413 limit exceeded, 415 unsupported file, 422 invalid payload, 502 provider error, 503 required component unavailable.
- Pagination: `limit` integer 1..100 (default 25), optional opaque `cursor` max 512 characters; response `{"items":[...],"next_cursor":null}`. Stable descending `created_at,id` ordering; no cross-company cursor reuse.
- Cookie-auth mutations require CSRF validation and an allowed Origin. Frontend sends credentials; do not put bearer/session credentials in localStorage. Validate authorization again on every endpoint and every file access.
- Each issue includes its own migrations, UI/backend/package work, integration adapters, fixtures, and checks. Do not wait for another issue to close. Implement against the contracts below; simulated adapters are explicit development-only substitutes, prohibited in production.
- Official validation reference: [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Zod basics](https://zod.dev/basics).


## Manager API and data specification

Session roles: `employee|manager`. All company settings are writable by managers in that company for the demo; reports are restricted further to assigned employees. Do not let a login claim or email domain create manager privileges. Bootstrap the first manager via trusted seed/provisioning; no public administrator promotion endpoint.

### Rules API and optimistic concurrency

Policy model is exactly `PolicySnapshot` in the engine spec; new companies enable all13 built-ins, version1, custom_rules empty. Policy reads come from the session company. All mutations are atomic and increment version exactly once.

| Endpoint | Exact input | Output |
|---|---|---|
| `GET /api/v1/rules` | Manager, no body |200 complete PolicySnapshot |
| `PATCH /api/v1/rules/builtins` | `{expected_version:int>=1,updates:[{rule_id:RuleId,enabled:StrictBool}]}` nonempty max13, IDs unique |200 new PolicySnapshot; stale version409 POLICY_VERSION_CONFLICT |
| `POST /api/v1/rules/toggle-all` | `{expected_version:int>=1,enabled:StrictBool}` |200 new PolicySnapshot toggling both built-ins and existing custom rules |
| `POST /api/v1/rules/custom` | `{expected_version,name,kind,pattern,case_sensitive,enabled}`; custom-rule constraints from engine, strict booleans |201 `{rule:CustomRule,policy_version:int}`; max100 custom rules, duplicate trimmed names409 |
| `PATCH /api/v1/rules/custom/{id}` | `{expected_version,...nonempty subset of name/kind/pattern/case_sensitive/enabled}` |200 same result; unknown fields422, foreign rule404 |
| `DELETE /api/v1/rules/custom/{id}` | Query `expected_version:int>=1`, no body |200 `{deleted_id:UUID,policy_version:int}`; keep historical rule identity on existing events |
| `POST /api/v1/rules/preview` | `{kind,pattern,case_sensitive,sample_text:str<=10000}`; draft pattern1..512 |200 `{matches:[{start:int,end:int}],count:int,truncated:bool}` max1000 displayed; no raw matched text returned, no save/LLM/report; invalid regex422, timeout422 RULE_TIMEOUT |

Exact rule uses literal matching; regex syntax is the same bounded evaluator as the engine. Reject empty-matching regex and whitespace-only names/patterns. Stale edits show a reload-required message in UI. `get_snapshot(organization_id)` is an internal authorized service, not an employee policy editing endpoint.

### Events and manager reports

`EventBatch` Pydantic contract: `{submission_id:UUID,organization_id:UUID,employee_id:UUID,policy_version:int>=1,occurred_at:UTC datetime,status:"completed"|"failed",findings:[Finding],failure_code:str|null}`. Fields derive from trusted guard/session. `Finding` uses engine spec without raw text; `failure_code` required for failed batches; findings may be empty. Internal event ingestion is a service call, not an unauthenticated HTTP endpoint. Unique `(organization_id,submission_id,policy_version)`; duplicate identical batches are no-ops, conflicting duplicates409. Keep submission summaries even if no PII was found.

`ReportEvent` public model: `{id,submission_id,employee:{id,display_name,email},occurred_at,policy_version,status,failure_code,findings:[{rule_id,category,count:int>=1,action:"redacted"|"allowed_disabled",locations:[SourceLocation]}],total_findings:int>=0}`. Group identical category/rule/action for display; keep original locations. Face count means detected face regions, not identified people.

| Endpoint | Exact input | Output |
|---|---|---|
| `GET /api/v1/reports` | Manager; pagination; optional employee_id UUID, category rule/category string1..80, action enum, from/to UTC timestamps; from<=to |200 paginated ReportEvent, only current assigned employees; filter naming is exactly `from_time`/`to_time` |
| `GET /api/v1/reports/summary` | Same filters without pagination |200 `{submission_count:int,failed_count:int,redacted_count:int,allowed_disabled_count:int,by_category:[{category,count}]}` from authorized dataset only |
| `GET /api/v1/reports/{event_id}` | Manager; UUID |200 ReportEvent; foreign/unassigned/missing404 |

### Persistence and implementation order

- Policy: company_id, version>=1, complete builtins JSON, custom_rules JSON, UTC updated_at. Initialize defaults idempotently when a company first needs policy; GET and internal snapshot service return the complete immutable snapshot.
- Event: UUID id/company_id/submission_id/employee_id, policy_version, occurred_at, status, failure_code nullable, validated findings JSON. Unique company/submission/policy version; index company/employee/time. Never persist matched raw text in report events.
- Implement policy/event models and migration → bounded rule evaluator integration → snapshot/event services → scoped endpoints → manager frontend → feature verification.
- `get_snapshot(organization_id)->PolicySnapshot` and `record(EventBatch)->None` are internal injection interfaces. Use typed synthetic SessionIdentity/assignment fixtures before real auth is connected. Do not implement a parallel login system.
- Tests cover versions, all-on/all-off, custom match/timeout/empty-regex rejection, assignments changing, cross-company filters/cursors, null failure fields, empty clean submissions, and duplicate batches.

## Exact file ownership

Each listed file has one issue owner. Update its directory index when implementing it.

| File | Responsibility |
|---|---|
| `apps/api/app/db/models/rule.py` | Company built-in overrides, custom rules, and policy versions (issue 4). |
| `apps/api/app/db/models/pii_event.py` | Submission findings/actions and idempotency identifiers (issue 4). |
| `apps/api/app/routes/reports.py` | Assigned-employee report and event detail endpoints (issue 4). |
| `apps/api/app/routes/rules.py` | Company rule CRUD/toggles and sample preview endpoints (issue 4). |
| `apps/api/app/schemas/reports.py` | Report filters, event summaries, and details (issue 4). |
| `apps/api/app/schemas/rules.py` | Company policy, custom rule, and preview request/response types (issue 4). |
| `apps/api/app/services/reporting.py` | Idempotent event ingestion and manager report queries (issue 4). |
| `apps/api/app/services/rules.py` | Policy snapshots/versioning and bounded custom-rule preview (issue 4). |
| `apps/api/tests/test_rules.py` | Policy versioning, isolation, preview, and invalid-pattern behavior (issue 4). |
| `apps/api/tests/test_reports.py` | Report authorization and idempotent event ingestion (issue 4). |
| `apps/web/src/features/reports/ReportFilters.tsx` | Employee, date, and category filters. |
| `apps/web/src/features/reports/EventList.tsx` | Show safe PII event summaries and counts. |
| `apps/web/src/features/reports/EventDetails.tsx` | Show source locations, policy/rule identity, and redacted/allowed actions. |
| `apps/web/src/features/reports/useReports.ts` | Fetch and paginate authorized manager reports. |
| `apps/web/src/features/rules/RuleToggles.tsx` | Individual and all-on/all-off company rule controls. |
| `apps/web/src/features/rules/CustomRuleEditor.tsx` | Create/edit exact-phrase and regex rules with case settings. |
| `apps/web/src/features/rules/RulePreview.tsx` | Preview matches against sample text before saving. |
| `apps/web/src/features/rules/useRules.ts` | Load, validate, save, and version company settings. |
| `apps/web/src/layouts/ManagerLayout.tsx` | Manager reports/settings/setup navigation (issue 4). |
| `apps/web/src/pages/ManagerReports.tsx` | Assigned-employee event reporting page (issue 4). |
| `apps/web/src/pages/ManagerSettings.tsx` | Company policy toggles and custom rules page (issue 4). |
| `apps/web/tests/rules.test.tsx` | Toggle, custom-rule validation, preview, and saving behavior (issue 4). |
| `apps/web/tests/reports.test.tsx` | Authorized reporting states and filters (issue 4). |
| `apps/api/migrations/versions/0003_company_policy_events.py` | Versioned company policies and PII event tables; company/employee foreign keys and idempotency constraints. |
| `demo/adapters/policy.py` | Supplied versioned company policies for independent workstreams. |
| `demo/adapters/reporting.py` | Synthetic idempotent reporting sink/source. |
| `docs/reporting-contract.md` | Define idempotent manager events and safe display fields. |
| `docs/rule-policy.md` | Define rule IDs, versions, enabled states, precedence, and regex limits. |

## Working independently

Use the documented interfaces and feature-owned development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.

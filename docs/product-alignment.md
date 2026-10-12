# Product alignment

Latest correction 2026-10-12: pseudofix is the engine base. Its UI is being restyled while preserving charts, diagrams and non-text evidence. One static manager page replaces auth/company account setup. Employee processing/full content remain local; manager-only reports/decisions go to Vercel. Manager approval gates the verified redacted download and cannot clear engine failures or unresolved findings.

Existing: teammate extraction, detection, redaction, audit/review, artifact verification and visualisations. Read README.md/phase reports for the actual format and detection limits.

Planned in this work: sparse chat theme, shared approved SVG, dark mode/loading/motion, mobile manager queue, revision-bound remote approval and local launcher. Update this status after end-to-end verification. Network interception and universal PII/document coverage remain unimplemented claims.

## Evidence from the current checkpoint

Implemented and verified:
- Employee chat and Details inspection overlay with focus trapping, Escape dismiss, and focus return.
- Static manager comparison queue, report publication, and approval service.
- Local artifact gate tied to audit revision and exact artifact SHA-256 (stale revision rejects approval with 409, download blocked until both local verification passes and manager approves).
- Full backend test suite passing: 312 passed in pytest (100%), including in-process manager integration and revision gating across PDF, DOCX, and PPTX formats.
- Full frontend test suite passing: 44 passed in vitest (100%), covering App chat/Details flows, manager page, decision filtering, and verification boundary.
- Both frontend modes pass TypeScript checks and Vite builds (`npm --prefix frontend run build` to `app/web/static`, `npm --prefix frontend run build -- --mode manager` to `frontend/dist`).
- Impeccable UI defect detection verified: 0 defects (`[]`).
- Preserved engine gap documented: `jane.smith@example.test` remained in returned text while the phone number was redacted. The engine classified/rejected the email-like value as URL; it has not been changed in this work, preserving the teammate engine and models.
- Standalone execution: `/Users/caf/Desktop/Run-PII-Guard.command` updated to point directly to `PII-Project` with `scripts/run-demo.py` runner.
- CI pipeline: `.github/workflows/test.yml` tests backend, frontend (both builds), and manager isolation. Hosted Vercel deployment remains pending actual deployment credentials.


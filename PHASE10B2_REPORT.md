# Phase 10B.2 — Privacy gateway product story

## A. Case-study story translated into UI

The interface now explains why Cadence inspects documents: its document-analysis agents support business operations, while organizational policy restricts PII from AI processing. The opening workspace and document overview communicate **inspect → resolve ambiguity → produce a redacted review copy → block unverified downstream use**.

The opening state includes the mixed evidence types—scanned policy PDFs, organizational PPTX and process DOCX—and an **Upload Business Artifact** action. A compact, collapsible “Why this document is being inspected” panel explains the policy context without promising complete discovery. No actual AI connection was added.

This is a presentation change within the existing application. Navigation, reviewer dialog, feedback API, source bounds, artifact generation and audit persistence remain the existing systems.

## B. Visual hierarchy changes

The loaded overview prioritizes the document hero and a red downstream-access card, rather than presenting every statistic equally. The unresolved REVIEW number and amber review action stand out. A cyan output card makes the redacted review copy the tangible result of inspection.

The hero uses 36px desktop type (32px on smaller desktop layouts), 32px decision counts, and a prominent AI ACCESS status. Section headings are approximately 20–22px; contextual copy is 13–15px. Tables and technical metadata remain compact. The mobile hero includes an early **AI ACCESS · BLOCKED** badge so the downstream restriction is visible before the larger card below.

The seven-stage pipeline now gives each stage a visible purpose: Business Artifact, Extract Content, Detect Sensitive Data, Human Resolution, Redact PII, Verify Artifact, AI Boundary. Actual measured stages retain their timings; the human and boundary stages do not invent inference times.

## C. Color system

| Meaning | Color |
| --- | --- |
| Near-black foundation | `#070A0F` |
| Surfaces | `#0E141B`, `#131B24` |
| Privacy gateway / primary action | `#22D3EE` cyan |
| Confirmed PII / supported technical success | `#22C55E` emerald |
| Human attention / unverified coverage | `#F59E0B` amber |
| Blocked downstream access | `#EF4444` red |
| Rejected / neutral findings | Slate; `#64748B` with lighter readable text |

Decision badges, funnel branches, review actions, source highlighting, map tiles and blocking states use these meanings consistently. Type-distribution rings retain a categorical palette; their colors describe entity groups, not safety. Gradients are limited to a subtle hero accent. Map color transitions and existing chart motion respect reduced-motion preferences.

## D. AI-boundary visualization

The overview visually connects **Business document → Cadence PII Guard → Redacted review copy → BLOCKED boundary → Document-analysis agent**. The agent is deliberately separated by the blocking gate and labeled “No AI connection is enabled.”

The hero, boundary, access card, pipeline and safety strip derive access from the existing backend clearance flags: `safe_for_llm`, `coverage_verified` and `downstream_export_permitted`. All remain false in the current backend, so all observed documents remain BLOCKED. Frontend presentation does not grant clearance.

The prominent access card shows actual supported-mapping verification, unresolved REVIEW count, coverage status and the reason that unverified sensitive information may remain. Green artifact checks never override the red AI gate.

## E. Document hero

The hero identifies the actual file/format, pages/slides/logical segments and current revision. Underscores are converted to spaces for display only; originals and API identity are unchanged. Detection completion is explicitly distinguished from PII coverage.

Raw candidates and effective confirmed/review/rejected counts come from backend summaries, not example values. The main action displays **Review N Findings** while retaining the accessible name **Review Findings** and its existing navigation behavior. Header download, regeneration and unavailable states are preserved. Human-added findings are noted when present.

The supplied PPTX browser run displayed **59 candidates, 25 confirmed, 15 needing review, 19 rejected, 9 slides**. After the demonstration confirmation it displayed **26 confirmed and 14 REVIEW**, with revision 1. These are observed product counts, not labeled accuracy measurements.

## F. Review storytelling

The existing Review Workspace now frames its task as “Human validation for ambiguous findings.” The selected finding separately displays its original automated assessment, human decision/correction status and actual effective result. An automated REVIEW appears as **Uncertain**, not as an already confirmed sensitive value.

The effective “Redacted” result requires an actual mapped replacement returned by the comparison API; CONFIRM alone is not treated as proof of an applied mapping. Rejected values are described as retained. The wording distinguishes reviewer rejection from automated-policy rejection, avoiding invented human decisions.

BEFORE / AFTER labels, amber source highlighting, a transformation arrow, cyan redacted context and actual replacement tags make the change visible. All context remains bounded through the existing endpoints.

Visual inspection showed the additional story initially pushed actions too far down. Confirm as PII and Mark False Positive were moved immediately below compact metadata, above the comparison. Phase 10B.1 automatic first/next selection, dialogs, loading guards, revision-aware feedback, regeneration notice and queue-complete CTA remain intact.

## G. Artifact outcome

The overview now has a larger **REDACTED REVIEW COPY** card with format/revision, actual applied-redaction count, mapping failures and verification failures. It retains both the prominent download and the detailed Artifact Verification view.

Downloads still use the opaque, current-revision artifact endpoint; no internal path is displayed. Every download area retains the nearby warning:

> Private review artifact — complete PII coverage has not been verified.

The output is an internal review artifact. It is not described as safe, fully sanitized or cleared for a downstream model.

## H. Governance timeline

Audit is presented as **Review & Governance Trail**, with the explanation that every human correction is preserved without overwriting the original automated decision. Original ambiguous findings, current unresolved counts, actual feedback events, decision transitions and revision state are visible.

The timeline continues to distinguish actual timestamped feedback from **current artifact state**. Generation/verification/revision details are displayed from backend state; no historical generation or verification events/timestamps were fabricated. Save/reload and original/effective audit semantics were preserved.

## I. Detector-quality presentation

The quality screen describes measured performance of the deterministic policy, and emphasizes deltas calculated from the existing policy 1.0/1.1 evidence:

- **+17.74 percentage points precision**
- **Same measured recall**
- **−11.90 percentage points REVIEW rate**

Existing values remain precision **98.16%**, recall **83.44%**, F1 **90.20%**, REVIEW rate **8.33%**. The synthetic-dataset disclaimer remains prominent and explicitly states that these are **not a claim of Cadence-document accuracy**. The Phase 10A evaluation/data were not changed.

## J. Test results

| Check | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests -q` | **284 passed**, 1 existing Starlette HTTPX TestClient deprecation warning; **85.69s** |
| `npm.cmd test` in `frontend/` | **36 passed**; 10.28s total |
| `npm.cmd run lint` in `frontend/` | Passed, zero warnings |
| `npm.cmd run build` in `frontend/` | TypeScript + Vite passed; JS 478.84 kB / 151.64 kB gzip; CSS 56.24 kB / 12.81 kB gzip |
| `node --test tests/frontend/core.test.mjs` | **4 passed**, zero failures |
| Protected engine/pipeline fingerprints | **45 unchanged** |
| Detector policy and evaluation dataset fingerprints | Unchanged |

The 30 previous React interaction tests were retained, with presentation selectors updated for the new labels. Six additional story tests cover the purposeful landing, actual hero counts/review CTA, blocked access with verified mappings and unknown coverage, decision funnel/map/output, human transformation/governance and calculated quality deltas/disclaimer.

An initial lint failure identified an unused icon import; it was removed. Final lint, tests and build pass. No engine, detector, redaction, audit, clearance or API payload behavior was modified.

Commands:

```powershell
# Project root:
.venv/Scripts/python.exe -m pytest tests -q
node --test tests/frontend/core.test.mjs

# In frontend/:
npm.cmd test
npm.cmd run lint
npm.cmd run build

# Actual commands also support the equivalent project-root invocation:
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build

# Existing isolated local backend on 8766, production frontend bundle:
node tests/frontend/phase10b2_browser.mjs
$env:CADENCE_UI_FIXTURE=(Join-Path (Get-Location) '.private_review_app/phase10b-fixtures/synthetic.docx')
$env:CADENCE_UI_COMPLETE='1'
node tests/frontend/phase10b1_browser.mjs
$env:CADENCE_UI_SYNTHETIC='1'
node tests/frontend/phase10b_browser.mjs
$env:CADENCE_UI_FIXTURE=(Join-Path (Get-Location) '.private_review_app/phase10b-fixtures/synthetic.pdf')
node tests/frontend/phase10b1_browser.mjs
```

## K. Browser acceptance

The real Chromium check uses the production React bundle, local FastAPI and actual default engines—no mocked HTTP or injected detectors. It uploaded the supplied Cadence PPTX, checked the purpose/hero/count-based CTA/blocking card, confirmed a REVIEW finding, verified next selection, revisited the corrected finding to inspect its actual replacement, opened governance/quality views, and downloaded/reopened the latest artifact.

| Run | Observed result |
| --- | --- |
| Supplied PPTX product-story flow | 59 / 25 / 15 / 19 → 59 / 26 / 14 / 19 (raw / confirmed / REVIEW / rejected), revision 0 → 1 |
| Supplied PPTX download | **68,314 bytes**, reopened with python-pptx |
| Fictional DOCX interaction regression | 7 / 3 / 2 / 2 → 7 / 4 / 1 / 2 after confirmation; complete queue at revision 2; 36,708-byte download reopened |
| Fictional DOCX broader regression | CONFIRM_PII, MISSED_PII, FALSE_POSITIVE and revision-3 save/reload passed |
| Fictional PDF interaction regression | 6 / 3 / 2 / 1 → 6 / 4 / 1 / 1 after confirmation; complete queue at revision 2; 1,222-byte download reopened |
| Runtime / CSP-security / failed API responses | **Zero** in these acceptance runs |
| Coverage / downstream status | **NOT ESTABLISHED / BLOCKED** throughout |

The actual browser sequence covers upload, why inspection is required, decisions demanding human review, confirmation, effective PII, regenerated artifact, direct download and preserved governance evidence. The real PPTX override is a demonstration on a new uploaded copy, not ground truth or a modification of an earlier saved reviewer decision. Supplied source files were not edited.

This is browser-controlled acceptance with visual inspection, not an independent interviewer usability study. The large scanned policy PDF was not OCR-processed again for a presentation change; small fictional PDF/DOCX fixtures verify format-independent interactions.

## L. Screenshots reviewed

Private screenshot evidence is under `.private_review_app/phase10b-ui/`; the final product-story run is identified by `latest-10b2.json`. Screenshots reviewed include:

- `empty.png`: purposeful opening, artifact types, upload and Inspect/Resolve/Protect.
- `overview.png`: document/decisions/review/download hero and prominent blocked access.
- `ai-boundary.png`, `purpose-pipeline.png`: enforcement barrier and visible purpose per stage.
- `review-auto-selected.png`, `human-transformation.png`: uncertainty, visible actions, actual human correction and replacement.
- `artifact-outcome.png`, `sensitive-distribution.png`: result download and stronger location distribution.
- `governance.png`, `detector-quality.png`: preserved decisions and measured-policy caveats.
- `laptop-overview.png`, `tablet-overview.png`, `mobile-overview.png`, `mobile-review.png`: responsive layout checks.

The final browser run checked **1540px desktop, 1280px laptop, 820px tablet and 390px mobile**; no horizontal overflow was observed. The red access badge was added within the mobile hero after visual inspection so the blocking state appears early. Screenshots with bounded source values remain private and are not distributed as public report artifacts.

## M. Remaining UX limitations

Mobile stacks the hero, access card, boundary, findings and context, so deeper evidence requires scrolling. Technical tables and metadata remain intentionally compact. The overview is longer because it now explains the gateway and output; the contextual policy panel can be collapsed.

Known queue completion and supported redaction verification still do not establish complete detection/PII coverage. Synchronous processing, OCR limitations, unsupported content and local single-reviewer constraints remain. There is no downstream AI integration or actual submission feature.

The existing running applications and their sessions were preserved. **Refresh the browser to load the newly built frontend.** No commit or push was performed.

**Completed:** the interface now shows the case-study chain from business artifacts through privacy inspection and human resolution to a redacted review copy, while visibly enforcing the unverified-coverage AI boundary. Phase 10B.1 interactions remain operational.

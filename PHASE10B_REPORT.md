# Phase 10B — React graphical privacy-review product

Implemented 12 October 2026 in `C:\Users\ivang\cadence-pii-guard-standalone`, separate from the Optiv/company-chat repository. React is the primary frontend; the previous vanilla UI is no longer served. Engines 1–5, pipeline/detector logic, policy v1.1, and evaluation evidence were preserved. No commits or pushes were made.

A fresh isolated preview is running at **http://127.0.0.1:8766** at handoff, using real default processing and a separate private demo directory. The normal documented launcher remains `run.py` on8765; the user's pre-existing8765 process was preserved.

**Completion: Phase 10B implemented and verified for the trusted local review application.** The product remains a privacy-review tool, not a coverage-certified or downstream-cleared system. Technical supported-mapping verification can pass while coverage remains **NOT ESTABLISHED** and downstream submission remains **BLOCKED**.

## A. Frontend Architecture

```text
run.py (unchanged, local Uvicorn)
  → app.main / FastAPI / existing processing and feedback API
      → app/web/static/index.html + bundle/ (built React primary UI)
          → React + TypeScript + Vite
              ├── Overview: measured pipeline, Bklit funnel/rings, privacy map
              ├── Documents: upload and saved-audit restoration
              ├── Review Queue: metadata table, bounded context, reviewer dialog, source selection
              ├── Audit: revisioned feedback timeline and explicit save
              ├── Artifact Verification: technical checks, download, current PDF preview
              └── Detector Quality: aggregate synthetic policy comparison
```

`frontend/src/App.tsx` owns navigation and document context. `hooks/useWorkspace.ts` loads current state, identity, metadata and audit history, guards obsolete document responses, and refreshes the product after backend operations. `lib/api.ts` centralizes the local header, safe errors, opaque URLs and serialized JSON requests. Types mirror `app/web/models.py` and the allowlisted pipeline/audit/artifact summaries. No Redux, Query framework, database, GraphQL, WebSockets, auth, Next.js, cloud frontend or AI service was added.

The frontend fetches all findings metadata through the existing paginated API (100 per page), then filters/paginates metadata locally. Only a selected finding/source window fetches bounded source text. Filtering does not classify candidates or reproduce reviewer logic. There is no background upload analysis or invented live stage progress.

Production build writes directly into `app/web/static/` with Vite `emptyOutDir`. It serves one React index and local hashed JS/CSS under `/assets/bundle/`. Vanilla `app.mjs`/`style.css` are removed from the serving directory; temporary development backup remains ignored under `.phase10b/legacy-ui/`. The existing pure offset/payload helper moved to `frontend/src/lib/core.mjs` and is used by React; its four original tests survive with the updated import path.

## B. Bklit Components Used

Selected **public MIT registry** components only:

| Component | Product use | Data |
|---|---|---|
| Bklit `FunnelChart` | Detection disposition overview | Actual `raw_detection_count`, `confirmed`, `review`, `rejected` |
| Bklit `RingChart` + `Ring` | Entity distribution | Actual loaded finding entity counts, including human additions |
| Animation/format helper closure | Short chart entry and number formatting | No sample or Studio data |

Source pinned to `bklit/bklit-ui@f7b3bd2999a5c993863f9cc5523c9cf60b9f3bc2`. Only nine required chart/helper files plus MIT notice and local utility were copied from the inspected public registry JSON. No complete repository clone, proprietary Studio code, chart editor or unused example datasets are included. The [upstream license boundary](https://github.com/bklit/bklit-ui/blob/f7b3bd2999a5c993863f9cc5523c9cf60b9f3bc2/README.md#license) distinguishes the MIT UI registry from proprietary Studio.

The small documented funnel patch scales geometry against the largest displayed disposition so human additions can exceed original raw detections without overflowing; API counts are unchanged. Clickable keyboard-accessible category overlays are application code. Ring legends include every present entity; rings show the five largest groups without inventing an “other” category.

shadcn Button, Card, Badge and Dialog are selected MIT reusable components from commit `993eb2c3151997ce08a49635c10fd8c8ef3713c7`. Aliases are adapted locally. Dialog's injected-style scroll lock was replaced with an external-CSS class so the existing strict CSP remains intact; Radix modal focus trapping remains. Full notices, copied filenames, provenance and local modifications are in [frontend/THIRD_PARTY_NOTICES.md](frontend/THIRD_PARTY_NOTICES.md).

Direct pinned registry copying was used instead of running an installer against a moving registry: it allowed inspection, exact revision attribution and copying only the necessary dependency closure. `components.json` also documents the shadcn/Bklit aliases and registry for future intentional additions. Optional Sankey was omitted because the disposition funnel and location map convey the story without an additional chart dependency.

## C. Design System

Near-black background, charcoal/cool-neutral panels, thin borders, compact typography, restrained mint/cyan accents, amber review/coverage, muted red blocking/error and green technical checks. Lucide icons support actions and stages. No neon gradients, ornamental landing-page imagery, external fonts, security score or encryption claim.

The sidebar gives a stable product context; the current document header shows format, location convention, revision and measured runtime. The four-part safety strip separates processing, technical artifact verification, coverage and downstream submission. Navigation/controls are keyboard accessible, Radix dialogs provide modal focus trapping, and native controls/semantic tables support normal interaction. Full accessibility certification was not performed.

CSS reduced-motion rules and Motion's user preference configuration constrain animation. Chart entry uses short configured transitions; the spinner becomes static under reduced motion. Color is supplemented by explicit decision/status text.

## D. Pipeline Visualization

The graphical narrative is **Upload → Extract → Detect → Human review → Redact → Verify → Audit**. Each stage has an icon, explicit state, measured timing where the API provides it, actual count or format/revision, and explanatory title text available on hover/focus.

Upload and human-review elapsed time are **not** fabricated: the API does not expose these measurements, so the UI uses `—` or `human-led`. Extraction/detection/redaction/verification/audit use the actual stage entries. While synchronous work is in flight, the UI displays “Processing document…” or “Regenerating review artifact…” and explains when measured timings will appear.

## E. Detection Analytics

The mandatory Bklit funnel uses actual backend counts and filters All/Confirmed/Review/Rejected on click. A visible note explains that the dispositions are **branches**, not sequential conversions. Counts are effective decisions; the human-added count is shown separately.

Entity rings and the legend derive solely from metadata returned by the findings API. No Cadence counts are embedded in UI code. Known review completion uses findings whose original automated decision was REVIEW and counts how many now have an effective non-REVIEW decision. The card says **“Known review findings resolved”**, not coverage complete. It also shows the backend queue count and warns that overlap/other issues can still require attention.

Zero results and failed/non-reviewable processing use explicit unavailable/empty states rather than invented successful zero-count results.

## F. Privacy Map

PDF tiles use pages; PPTX tiles use slides; DOCX uses the API's **logical segment** terminology. No physical DOCX pages are fabricated. All extracted locations appear, including those with no known findings.

Each tile shows known count, confirmed/review/rejected counts and review-required emphasis. Density classes are relative to actual per-location counts and are expressly not risk scores. Hover titles list entity types and disposition counts. Click filters the review workspace to that location. Legends supplement color.

## G. Review Workflow

The split workspace has a paginated metadata table and bounded detail panel. Columns include finding ID/entity, location, confidence or human-added state, recognizer, original automated decision, effective decision and review state/correction marker. Decision, entity, location and metadata search filters remain available. Search input is kept local rather than sending candidate values in query strings.

Selecting a finding fetches its existing bounded detail and actual mapped comparison. The review dialog records reviewer ID, optional reason and CONFIRM_PII/FALSE_POSITIVE. Payloads use the existing `expected_revision`, finding ID and action contract. The frontend does not decide classifications, change policies or learn from corrections.

After feedback, current state/findings/audit/documents reload; counts, queue, charts, revision and artifact availability update from the backend response. Detail/source windows are invalidated on revision/document changes. A visible feedback sequence explains **human decision → artifact result → supported mapping checks → audit revision**. If regeneration fails, the notice says the artifact needs attention; it does not falsely claim regeneration passed.

Stale revision409 refreshes the current review and asks the reviewer to reopen the finding. Repeated operations are prevented while processing. Old document loads are guarded from overwriting newly selected context.

## H. Redaction Comparison and Missed PII

The original finding context is bounded by the existing API (120 characters before/after; candidate up to240). React text/mark rendering highlights the candidate without `dangerouslySetInnerHTML`.

One minimal additive endpoint was necessary for truthful comparison:

`GET /api/documents/{id}/findings/{finding_id}/comparison`

It returns only finding ID, current review state, actual mapped replacement (up to240) and actual Engine4 redacted-page context (up to480). It reads existing redaction mappings/output; it does not reimplement redaction, expose tags from an entire document, return paths/hashes or change engine behavior. For unresolved/unmapped findings it returns null comparison fields; the UI explains that no replacement is applied rather than faking a redacted string. Three-format mapping tests and unresolved/unknown-finding checks cover it.

Missed-PII flow remains source based: choose a page/slide/logical segment, fetch a bounded1600-character window, select1–1000 characters, choose an entity and submit. DOM selection counts Python Unicode codepoints across highlights/non-BMP characters. The selected text is visible only in the local review dialog; POST sends existing location/start/end/entity/reviewer/reason/revision fields, **not text or replacement values**. Engine5 remains the validator.

PDF uses the actual current artifact in a browser iframe. DOCX/PPTX use bounded extracted textual context, not a fake Office renderer. Revision in artifact URLs is a refresh/cache-busting hint; the existing endpoint always serves the current session artifact, not a separately implemented historical-file API.

## I. Audit Timeline

The graphical timeline retains automated detection context and shows each actual feedback event's timestamp, action, finding ID, reviewer, previous/new decision and reason. The current artifact is shown as current state, explicitly **not** a separately timestamped historical backend event. No invented regeneration timestamps or per-event verification results are attached to prior events.

Explicit Save audit and Documents/saved references preserve the existing persistence workflow. Real browser testing exposed one pre-existing API serialization bug: restored feedback actions are strings, while `/audit` assumed an enum `.value`. A one-line serializer now accepts the existing enum/string representations. The engine/loader were not modified. A new test saves a feedback-bearing audit, reloads it, fetches the timeline successfully and proves the detector was not rerun.

## J. Artifact Verification

The dedicated view separately lists artifact generated, reopened, supported mapping, verification completed, mapping/verification failures, residual counts and actual replacements. Unsupported structures are visible. Downloads are disabled when the backend says no artifact is available.

**“PASSED” is scoped to supported technical mappings**, not full `artifact_verified`, complete known review, or PII coverage. Coverage **NOT ESTABLISHED** and downstream **BLOCKED** appear in their own amber/red panels with `safe_for_llm:false` and `downstream_export_permitted:false`. This distinction also appears in the persistent safety strip/footer.

## K. Detector Quality View

`tools/export_detector_quality.py` extracts only aggregate values from the unchanged `detector_eval_baseline.json` and `detector_eval_hardened.json` into `frontend/src/lib/detector-quality.json`. It excludes source examples, fingerprints/hashes and detailed evaluation records.

| Metric | Policy1.0 | Policy1.1 |
|---|---:|---:|
| Precision |80.42%|98.16%|
| Recall |83.44%|83.44%|
| F1 |81.90%|90.20%|
| Review rate |20.24%|8.33%|

Cards and paired comparison bars visibly say **“Measured on synthetic labeled evaluation dataset”**,420 cases, **not real Cadence-document accuracy**, and no coverage attestation. These are static evaluation measurements, not live accuracy inferred from uploads or reviewer actions. The metadata generator does not change policy/evaluation data.

## L. API Integration and Migration

All existing Phase9 APIs remain: config; upload/list/get/review; paginated findings/detail/source; feedback/missed-pii; artifact; audit/save; saved-audits/load-audit. Opaque IDs remain the only document/audit references.

Backend changes are limited to the typed bounded comparison endpoint and restored-action serialization fix. Existing route contracts, request boundaries, pipeline methods and `run.py` are preserved. No detector/engine rewrite, schema/database addition or processing dependency was introduced.

JSON requests are serialized because the existing local launcher limits connections to4 and processing is synchronous. Initial parallel React requests produced overload responses in a real-browser run; serialization resolved them without weakening/changing the launcher. Vite's development proxy rewrites only the exact trusted `http://127.0.0.1:5174` Origin to the local backend Origin, leaving foreign Origins untouched. Production is same-origin FastAPI hosting.

Exact normal commands are in the updated README:

```powershell
# Project root
Set-Location frontend
npm.cmd ci
npm.cmd run build
Set-Location ..
.venv/Scripts/python.exe run.py
# Open http://127.0.0.1:8765
```

Development: backend on8765; `npm.cmd run dev` in frontend; open `http://127.0.0.1:5174`. Existing server processes need a normal restart to load the small API additions; desired ephemeral reviews should be explicitly saved first. This work did not terminate the user's pre-existing8765 process or silently discard its in-memory reviews. Real-browser acceptance used an isolated current-code server on8766 and restricted private working data.

## M. Security Preservation

- Loopback Host/Origin boundary, local mutation header, upload bound, opaque IDs, revision guards, private file checks, no-store and strict CSP remain.
- No absolute artifact/source/audit paths or hashes were added to public response types or UI URLs. Artifact/preview URLs contain opaque session ID and technical flags/revision only.
- Source context is bounded and fetched on selection; no full-document original text dump, raw-value analytics, browser logging or sensitive server exception serialization was added.
- React text rendering is used; no HTML injection. Reason/reviewer inputs go only to existing local feedback endpoints.
- Radix's inline scroll-lock stylesheet initially caused a CSP violation. External-CSS locking fixed it; no `unsafe-inline`, remote CDN, CSP relaxation or extra network service was introduced. Browser tests explicitly check CSP/runtime errors and failed API responses.
- Protected source hashes were captured before work for engines/pipeline and evaluation evidence; final comparison showed no changes. Original supplied documents were not edited; uploads use private copies.
- Plaintext/local/demo/unsupported-content limitations remain; no encryption, production multi-user security or universal PII claims were added.

## N. Responsive Design

Desktop uses fixed sidebar, contextual header, analytics grid and split review panel. Laptop/tablet simplify columns and stack details when needed. Small screens use a compact horizontally scrollable nav, stacked cards/detail, wrapping controls and a contained table scroll area. The **page itself** has no horizontal overflow; table content can scroll independently rather than truncating required fields.

Real Chromium checks/screenshot inspection covered1540 desktop,1280 laptop,820 tablet and390 mobile widths. Overview, review/dialog, timeline, verification, quality, PDF preview and mobile review were captured privately. Reduced-motion support is both CSS and Motion configuration. No formal assistive-technology/device certification was performed.

## O. Test Results

| Check | Result |
|---|---|
| Existing Python suite before additions |279 passed,1 existing Starlette TestClient deprecation warning;69.90s |
| Final Python suite |284 passed,1 existing deprecation warning;77.93s; `.phase10b/python-tests-final.log` |
| Focused review API after additions |24 passed,1 existing warning;42.30s |
| React/Vitest |19 passed; covers render, multipart upload/header, measured dashboard/funnel SVG, filters/map, modal, both feedback actions, Unicode source selection, offset-only MISSED_PII, timeline, download/preview URLs, safety distinction, metrics disclaimer, save/reload, error/unavailable states,409 |
| Original pure frontend helper tests |4 passed; Unicode offsets, empty/oversized ranges, feedback contracts, stage labels preserved |
| TypeScript + production build |Passed; Vite7.3.7 final bundle about466KB JS/149KB gzip,43KB CSS/10KB gzip |
| ESLint |Passed with0 warnings; application/types/tests linted, selected upstream vendor files excluded from local lint conventions |
| npm audit |0 known reported vulnerabilities after upgrading initial tools to patched Vite7.3.7/Vitest4.1.11 |
| Python compileall for web/helpers |Passed |
| Protected engine/pipeline/evaluation fingerprints |45 protected files unchanged; dataset byte fingerprint also matches the unchanged Phase10A report |

Initial failures were corrected: test matchMedia setup restoration; an exact accessible-name selector that overlooked the queue count; a Windows encoding conversion while relocating the legacy test import; the vendor dialog CSP injection; initial connection bursts; and the restored-feedback timeline serializer. No failing test was removed or weakened to hide a production defect.

### Real Chromium + real backend acceptance

`tests/frontend/phase10b_browser.mjs` uses installed Chrome in a fresh headless profile and actual multipart/API workflows. No injected detector/engine or mocked HTTP is used. Profiles/screenshots/downloads/summaries stay under `.private_review_app/phase10b-ui/`.

| Document/run | Actual before/after confirmation | Other verified behavior |
|---|---|---|
| Supplied Cadence PPTX |59 raw;25→26 confirmed;15→14 REVIEW;19 rejected|Artifact regenerated,68,314-byte download, timeline, saved revision1/reload, metrics disclaimer, no overflow/runtime/CSP/API errors |
| Fictional PDF |6 raw;3→4 confirmed;2→1 REVIEW;1 rejected|1,222-byte download, actual browser PDF preview, save/reload, responsive checks, no errors |
| Fictional DOCX |7 raw;3→4 confirmed;2→1 REVIEW;2 rejected|36,708-byte download, logical-segment selection, save/reload, responsive checks, no errors |
| Fictional DOCX all-actions run |Same initial confirmation, then MISSED_PII and FALSE_POSITIVE|Exact SecretToken selection through DOM/API, human finding, revision3 save/reload, all three feedback actions, zero failed API responses/runtime/CSP errors |

Numbers above are **observed test evidence**, not hardcoded frontend metrics or real-document accuracy. The supplied PPTX confirmation is a demonstration override on an uploaded copy, not ground truth. Synthetic browser fixtures are generated by `tools/create_phase10b_fixtures.py` without modifying the Phase10A dataset. Backend tests also exercise actual PDF/DOCX/PPTX artifact mapping, all feedback actions, source validation and stale conflicts with controlled analyzers; those are distinguished from the real default-model browser runs.

Primary commands:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
node --test tests/frontend/core.test.mjs
# In frontend:
npm.cmd test
npm.cmd run lint
npm.cmd run build
npm.cmd audit
# Against the isolated current-code local server:
node tests/frontend/phase10b_browser.mjs
# Set CADENCE_UI_FIXTURE for generated PDF/DOCX;
# CADENCE_UI_SYNTHETIC=1 additionally exercises selection/missed/false-positive.
```

## P. Demo Workflow (10–15 Minutes)

1. Start the built local app; show the local-only boundary and separate safety strip.
2. Upload the supplied PPTX for a short real demonstration. Explain synchronous processing, then show measured stages and the Upload→Audit narrative.
3. Show the real funnel, entity rings, known-review completion and slide map. Explain branch counts and why completion is not coverage.
4. Click Review or a source tile; inspect original/effective decisions and bounded context. Open the reviewer dialog and record an intentional human decision/reason.
5. Show the immediate confirmation/queue count change, revision increment and artifact-regeneration notice. No Presidio rerun or automatic learning is introduced.
6. Open Audit: show the actual feedback event and current artifact state. Save the revision and restore through Documents to demonstrate persistence.
7. Open Artifact Verification: explain technical mapping checks, residual/unsupported counters and actual download. For PDF show the native browser review copy; for Office show bounded extracted context.
8. Demonstrate source selection/MISSED_PII with the fictional acceptance document if a controlled example is needed. Do not make arbitrary human corrections to a real document and call them labels.
9. Show Detector Quality: policy1.1 metrics and policy1.0 comparison, with the synthetic-only disclaimer visible.
10. End with **supported-mapping artifact verification PASSED / coverage NOT ESTABLISHED / downstream submission BLOCKED**.

## Q. Known Limitations

The inherited local single-reviewer model, plaintext restricted storage, process-local sessions/lock, synchronous OCR/no job cancellation, source-retention requirement and unsupported image/Office/PDF content remain. Long PDF OCR can take substantial time. UI timing cannot expose real stage progress while a synchronous upload is in flight. The frontend loads all **metadata** to build complete maps/charts; very large candidate sets can take additional pagination time.

Charts are descriptions of observed candidates, not a privacy risk/safety score. Human-added findings can exceed original raw detections and are labelled separately. Rings visualize the largest five entity groups while the legend lists all. Original source values remain sensitive even in a bounded authorized local window. DOCX locations are logical; no Word/PowerPoint visual fidelity renderer was added. Unsupported/unmapped replacements show no fabricated comparison.

Artifact downloads remain private review copies, not approved downstream exports. Current artifact state is not a reconstructed per-feedback historical verification log. Optional Sankey is intentionally absent. Accessibility/production deployment/multi-user isolation/full accuracy certification are outside this phase. A running old8765 server needs a normal operator restart; it was preserved rather than discarding unsaved user reviews during this task.

## R. Completion Status

**Phase10B complete for the stated local graphical-redesign scope.** The React primary UI builds/tests/lints, selected MIT Bklit components use actual data, real supported-format upload/review/artifact/audit workflows run, reviewer feedback visibly changes product state, source selection and all feedback actions survive, detector metrics carry correct caveats, and technical verification remains separate from coverage/clearance.

The work did not modify Engines1–5, detector thresholds/policy, Phase10A evidence, or clearance flags. No Qwen/other AI, automatic learning, auth, database, cloud/network deployment, commit or push was introduced. This is completion of the frontend phase, not a claim that the underlying privacy system discovers all PII or is production cleared.

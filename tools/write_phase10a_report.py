"""Render the measured Phase 10A report from public aggregates only."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    read=lambda name:json.loads((ROOT/name).read_text(encoding='utf-8'))
    baseline=read('detector_eval_baseline.json'); final=read('detector_eval_hardened.json')
    real=read('detector_documents_hardened.json'); risk=read('detector_documents_risk_checks.json')
    lines=['# Phase 10A — PII detector evaluation and hardening',
        '\nMeasured 2026-10-12. Policy 1.0 → 1.1. Synthetic precision improved with unchanged recall. '
        'Real Cadence review burden remains substantial, and one partial email now requires review. '
        '**No document is cleared for downstream submission.**',
        '\n## A. Existing Detector Architecture',
        '\nThe actual implementation is `app/engines/pii_detection/`. One reusable Presidio '
        '`AnalyzerEngine` analyzes nonblank pages in English and registers the custom employee recognizer once. '
        'The default analyzer score threshold is **0**, unchanged. Registered recognizers: '+
        ', '.join(r['name'] for r in baseline['recognizers'])+'.',
        '\nEngine 3 validates source offsets, exact source slices, entity syntax, finite confidence in [0,1], '
        'and recognizer metadata. Candidates are sorted by page-local span/entity and each receives exactly '
        'one disposition. Engine 3 retains duplicate and overlapping candidates; Engine 4 resolves covering '
        'overlaps, preserves superseded evidence, and blocks unresolved crossing overlaps. Raw = CONFIRM + REJECT + REVIEW.',
        '\nBaseline routing: out-of-policy types → REJECT; exact `EMP-` plus five digits → CONFIRM; '
        'business labels/acronyms, email-containing PERSON spans and numeric PERSON spans → REJECT; '
        'structured multi-token names → CONFIRM; other PERSON spans → AMBIGUOUS → REVIEW. '
        'Bank and driver-license candidates always → REVIEW, with different reasons for presence/absence of '
        'supporting context. All other policy entity types → CONFIRM using Presidio evidence. '
        'There was no email/phone structural validation or independent confidence threshold.',
        '\nValidation context is bounded to 200 characters on each side of the candidate. Policy includes '
        'PERSON, EMAIL_ADDRESS, PHONE_NUMBER, EMPLOYEE_ID, US_SSN, US_PASSPORT, US_DRIVER_LICENSE, '
        'US_ITIN, US_BANK_NUMBER, IBAN_CODE, CREDIT_CARD and MEDICAL_LICENSE. Dates, locations/addresses, '
        'organizations, URLs and other entities are outside this redaction policy. Deprecated LLM metadata '
        'exists only for old snapshots; current detection uses no generative model. Engine 5 preserves '
        'automated decisions and replays explicit reviewer events into separate effective state.',
        '\n## B. Evaluation Dataset',
        '\n`tests/data/detector_evaluation.json`: **420 synthetic text cases, 320 positive gold spans**, '
        '672 baseline raw candidates. Seed **10010**, version **synthetic-1**. Category-stratified case split '
        'uses rounded 70% groups: **299 development / 121 held-out**; 224 / 96 gold spans. '
        'Each case records exact offsets/entities, useful negative spans, category, notes and split. '
        '`tools/build_detector_dataset.py` generates labels independently of detector output.',
        '\nCases cover names/titles, email, phone, employee IDs, bank accounts, SSN-like values, malformed '
        'identifiers, OCR concatenations, headers, footers, tables, repeated values, departments, organizations, '
        'roles, committees, projects, abbreviations, dates, addresses and numeric business amounts. '
        'Names/digits are invented; contacts use example.com and fictional 555-01xx telephone ranges. '
        'No real-document PII was copied. Addresses/dates are deliberately negative under the current '
        'policy, not evidence that the product discovers all address/date PII.',
        '\nThe dataset and tools are public, repository-ready files. This workspace has no `.git` metadata '
        '(`git status --short` reports “not a git repository”), so tracked status cannot be verified; '
        'no repository was initialized and no commit/push was performed. Templates and invented values recur '
        'across categories/splits: the held-out score measures generalization within these synthetic scenarios, '
        'not an independent financial-document benchmark. There are no positive passport/license/card/IBAN '
        'gold labels; their coverage remains unevaluated.',
        '\n## C. Metric Definitions',
        '\nMatch = exact `(case ID, start, end, entity type)` using Python code-point offsets. '
        'Each gold and predicted key is scored once, regardless of duplicate recognizers. A wrong boundary '
        'or type creates a false positive and leaves the gold span as a false negative. '
        'TP = confirmed ∩ gold; FP = confirmed − gold; FN = gold − confirmed. '
        'Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2PR/(P+R); zero denominators return 0, '
        'so unsupported/no-gold entities are not assessed as having perfect precision or recall.',
        '\nCONFIRM/REJECT/REVIEW rates use raw candidates as denominator and retain duplicate candidates '
        'for accounting. Human-assisted **potential recall** = gold ∩ (confirmed ∪ REVIEW) / gold; '
        'REVIEW is never an automated TP. Review true/false span counts are separately reported. '
        'Potential recall assumes correct human adjudication, not that such adjudication occurred. '
        'No aggregate accuracy or labeled real-document recall is claimed.',
        '\n## D. Baseline Results',
        '\nBaseline JSON and readable Markdown were saved **before detector edits**: '
        '`detector_eval_baseline.json` / `.md`. They contain source fingerprints, dataset digest, '
        'per-case candidate metadata, recognizer registry, metrics and timings. Baseline historical PDF '
        'detections were reused only after matching source SHA and original detector source fingerprints; '
        'DOCX/PPTX baseline extraction/detection was saved privately before hardening.',
        '\nOverall baseline: 267 TP, 65 FP, 53 FN; CONFIRM 332, REJECT 204, REVIEW 136. '
        'FP categories: malformed email 20, numeric business values 25, project codes 20. '
        'FN categories: account 20, OCR name 20, table 7, person 2, adjacent email 2, header 1, '
        'duplicate context 1. These are automated-confirm FNs; all 20 account gold spans were in REVIEW.',
        '\n## E. Review-Reason Analysis',
        '\nSynthetic baseline: 135 context-sensitive identifiers and 1 ambiguous PERSON. Reasons: '
        '115 `identifier_without_supporting_context`, 20 `identifier_requires_contextual_review`, '
        '1 `person_requires_contextual_review`. Hardened: 55 identifiers + 1 PERSON; '
        '35 without supporting context, 20 with supporting context, 1 ambiguous PERSON. '
        'True reviewed gold spans stay **20**; non-gold review spans fall **116 → 36**. '
        'These categories derive from entity/reason metadata, not sensitive source text.',
        '\nReal baseline reasons: PDF 87 ambiguous PERSON, 83 identifiers without context, 2 with context; '
        'DOCX 23 ambiguous PERSON + 287 driver-license candidates without context; PPTX 15 ambiguous PERSON. '
        'No unsupported claim is made that every low-score identifier is false. The 287 DOCX numeric '
        'candidates remain REVIEW because the new rules cannot establish a safe contextual rejection.',
        '\n## F. Detector Changes',
        '\nPolicy constant `DETECTOR_POLICY_VERSION = "1.1"` is reported with source fingerprints in '
        'evaluation and diagnostic results. Existing audit schemas/fingerprints were preserved.',
        '\n- Email: confirm conservative unquoted mailbox structure; reject consecutive-dot/leading-dot '
        'local parts; unfamiliar syntax and suspected partial spans stay REVIEW.\n'
        '- Employee IDs: ASCII five-digit format and stronger recognizer boundaries prevent embedded '
        'alphanumeric/hyphen suffix matches; injected partial spans stay REVIEW.\n'
        '- Numeric context: reject phone/bank/license/passport candidates only with adjacent explicit '
        'money-field-plus-currency evidence or a labeled internal/project/release code prefix. '
        'A remote business word cannot trigger rejection.\n'
        '- Phone: plausible digit count/character structure; unfamiliar formats stay REVIEW. '
        'Presidio evidence is retained without lowering thresholds.\n'
        '- PERSON: institutional suffix evidence rejects organization/department-like full spans; '
        'low-confidence (<0.5) PERSON stays REVIEW. Unknown single tokens/OCR names remain REVIEW '
        'if emitted. No literal synthetic-name or Cadence-specific exceptions were added.\n'
        '- Exact relative context offsets prevent repeated values from borrowing the first occurrence’s '
        'field evidence. All raw duplicates remain accountable; redaction overlap rules are unchanged.',
        '\nDevelopment output was examined before freezing the final rules. A small employee boundary '
        'hardening followed that development run; the final all-case evaluation includes the resulting '
        'development metrics and frozen source fingerprints. Held-out cases were not used to choose '
        'literal fixes; no detector changes followed the held-out evaluation.',
        '\n## G. Development-Set Results']
    def table(a,b):
        out=['\n| Metric | Baseline | Hardened | Change |','| --- | ---: | ---: | ---: |']
        for key,label in [('precision','Precision'),('recall','Recall'),('f1','F1')]:
            out.append(f'| {label} | {a[key]*100:.2f}% | {b[key]*100:.2f}% | {(b[key]-a[key])*100:+.2f} pp |')
        out.append(f"| REVIEW rate | {a['rates']['REVIEW']*100:.2f}% | {b['rates']['REVIEW']*100:.2f}% | {(b['rates']['REVIEW']-a['rates']['REVIEW'])*100:+.2f} pp |")
        for key,label in [('tp','True positives'),('fp','False positives'),('fn','False negatives')]:
            out.append(f'| {label} | {a[key]} | {b[key]} | {b[key]-a[key]:+} |')
        out.append(f"| Potential recall | {a['potential_recall']*100:.2f}% | {b['potential_recall']*100:.2f}% | {(b['potential_recall']-a['potential_recall'])*100:+.2f} pp |")
        return out
    lines+=table(baseline['splits']['development'],final['splits']['development'])
    lines+=['\n## H. Held-Out Validation Results']+table(baseline['splits']['heldout'],final['splits']['heldout'])
    lines+=['\nHeld-out CONFIRM / REJECT / REVIEW: **96 / 56 / 34 → 79 / 93 / 14**. '
            'Six bank-account gold spans remain reviewed; non-gold review spans decrease 28 → 8. '
            'Remaining 18 automated FNs: 12 PERSON, 6 account. The remaining FP is an unsupported-context '
            'passport interpretation of a numeric business value. No tuning was performed after this result.',
            '\n## I. Before/After Comparison']+table(baseline['overall'],final['overall'])
    lines+=['\nOverall CONFIRM / REJECT / REVIEW: **332 / 204 / 136 → 272 / 344 / 56**. '
            'CONFIRM rate 49.40% → 40.48%; REJECT rate 30.36% → 51.19%. '
            'Raw count stays 672; duplicate predictions 0 in this dataset. Five remaining confirmed '
            'false positives are passport-like numeric business values. No automatic recall improvement '
            'occurred; OCR and boundary/type errors remain.',
            '\n| Entity | Baseline TP/FP/FN | Hardened TP/FP/FN | Baseline P/R/F1 | Hardened P/R/F1 | Hardened potential recall |',
            '| --- | --- | --- | --- | --- | --- |']
    for e,a in baseline['overall']['per_entity'].items():
        b=final['overall']['per_entity'][e]
        m=lambda x:'/'.join(f'{x[k]*100:.2f}%' for k in ['precision','recall','f1'])
        counts=lambda x:'/'.join(str(x[k]) for k in ['tp','fp','fn'])
        lines.append(f"| {e} | {counts(a)} | {counts(b)} | {m(a)} | {m(b)} | {b['potential_recall']*100:.2f}% |")
    lines+=['\nPer-split entity metrics and complete FP/FN/review categories are in both evaluation JSON files. '
        'All positive email/employee/phone/SSN gold spans stay covered on this synthetic dataset. '
        'PERSON automated recall is 79.38% overall / 75.00% held-out. '
        'Department/business false positives were already zero in the emitted synthetic baseline candidates; '
        'injected validator tests demonstrate the institutional rule without claiming measured PERSON '
        'precision improvement where none occurred.',
        '\nRepresentative public synthetic evidence: `ada@example.com` confirms; '
        '`ada..example@example.com` rejects; `Revenue amount: 2125550101 dollars` rejects a numeric phone '
        'interpretation while `Telephone: 2125550101` retains it. `EMP-12345-extra` does not become a '
        'custom employee candidate. `Smith Risk Committee` rejects as an institutional full span; '
        '`Brightwell` remains REVIEW. `Blue Horizon` can still confirm as a two-word PERSON despite '
        'project meaning—a known limitation. OCR `JohnSmith` often produces no PERSON candidate at all.',
        '\n## J. Real Cadence Diagnostic',
        '\nNo human overrides were applied. Private cache `.private_detector_eval/` stores source '
        'fingerprints, extraction, baseline/new detection, redaction and bounded changed-decision evidence '
        'under restricted local permissions and gitignore rules. Aggregate-only public JSON files are '
        '`detector_documents_baseline.json`, `detector_documents_hardened.json`, and '
        '`detector_documents_risk_checks.json`. Source byte hashes were checked unchanged.',
        '\n| Document | Raw old/new | Confirm old/new | Reject old/new | REVIEW old/new | Changes | Applied old/new |',
        '| --- | ---: | ---: | ---: | ---: | --- | ---: |']
    for kind in ['pdf','docx','pptx']:
        d=real[kind]; a=d['before'];b=d['after'];r=risk[kind]
        changes=', '.join(f'{k}: {v}' for k,v in d['changes'].items()) or 'None'
        lines.append(f"| {kind.upper()} | {a['raw']}/{b['raw']} | {a['confirmed']}/{b['confirmed']} | {a['rejected']}/{b['rejected']} | {a['review']}/{b['review']} | {changes} | {r['old_applied']}/{r['new_applied']} |")
    lines+=['\nNew confirmations: **0** for each document. PDF: one new rejection from REVIEW and one '
        'new REVIEW from CONFIRM, two changed decisions; no added/removed raw candidates. '
        'DOCX/PPTX: no new confirmations, rejections, REVIEW findings or decision changes. '
        'Accounting is consistent for all six distributions. These counts measure distribution changes, '
        'not precision/recall on real documents.',
        '\n| Format | Entity | CONFIRM/REJECT/REVIEW before | CONFIRM/REJECT/REVIEW after |',
        '| --- | --- | --- | --- |']
    for kind in ['pdf','docx','pptx']:
        for entity,a in real[kind]['before']['entities'].items():
            b=real[kind]['after']['entities'][entity]
            counts=lambda x:'/'.join(str(x.get(k,0)) for k in ['CONFIRM','REJECT','REVIEW'])
            lines.append(f'| {kind.upper()} | {entity} | {counts(a)} | {counts(b)} |')
    lines+=['\nPDF: 35 cached OCR pages, 107,571 page characters, 3,396 OCR blocks. OCR was not rerun. '
        'DOCX: 2,610 logical extraction segments; PPTX: 9 slides. '
        f"New detection times: PDF {real['pdf']['seconds']:.6f}s, DOCX {real['docx']['seconds']:.6f}s, "
        f"PPTX {real['pptx']['seconds']:.6f}s. Three-format comparison total {real['elapsed_seconds']:.6f}s. "
        'The baseline PDF time is zero because historical detections were reused, not because inference '
        'takes zero time. No Qwen or other generative inference occurred.',
        '\nKnown-risk check: in redacted **extracted text**, candidate instances whose exact confirmed '
        'value occurs anywhere in output are PDF EMPLOYEE_ID 13 → 13, PERSON 72 → 72, '
        'EMAIL_ADDRESS **4 → 7**; DOCX PERSON 2 → 2; PPTX PERSON 1 → 1. These are instance-level '
        'warnings (duplicates/substring/context effects), not distinct missed values or labeled false '
        'negatives, and differ from Phase 8 artifact selectable-text checks. '
        '**The partial email moved to REVIEW is no longer automatically replaced, increasing residual '
        'risk pending human review.** This is a safety-preserving unresolved finding, not a claim of '
        'improved real-document coverage. Changed source evidence stays private; no sensitive candidate '
        'inventory or full unredacted page was printed.',
        '\nAll three `redaction_complete=False` and `safe_for_llm=False`. Blocking issues remain '
        '172 / 310 / 15. Existing unsupported artifact structures, image/OCR risks and residual warnings '
        'are not cleared. Artifacts were not regenerated solely to change detector counts in this phase; '
        'PDF/DOCX/PPTX artifact and feedback integration are covered by the full regression suite.',
        '\n## K. Reviewer Feedback Dataset Export',
        '\n`app/engines/audit/feedback_export.py::export_feedback` and '
        '`tools/export_reviewer_feedback.py` export **actual reviewer events only**. Rows contain entity, '
        'automated/reviewer decisions, action, retained recognizer name/method, confidence, source '
        'category/format and explicit policy version. The existing candidate model retains recognizer '
        'name/method, not the original full Presidio metadata dictionary. No source path, document ID, '
        'reviewer identity, free-text reason or candidate value is exported by default.',
        '\nContext requires explicit `--include-context` / `include_context=True`, is bounded to 400 '
        'code points and records relative offsets/truncation. Output is plaintext under the existing '
        'restricted private AuditStore permissions with a directory `.gitignore`; public/static/network '
        'or symlink paths fail closed. Existing exports are not overwritten. No encryption or automatic '
        'label acceptance is claimed. Validation replays audit feedback without changing decisions or rules.',
        '\nExecuted a metadata-only export of one existing Phase 9 demonstration event to '
        '`.private_feedback/phase10a-demo/feedback_dataset.json`. It uses its original policy version 1.0 '
        'and category `demonstration`; **this override is not gold ground truth**. Existing audits were '
        'not edited. Historical versions default to `unknown-legacy` unless the operator knows the original '
        'version. Curate genuine reviews into later labeled examples before any deliberate policy update.',
        '\n## L. Full Test Results',
        '\n`.venv/Scripts/python.exe -m pytest tests -q`: **279 passed, 1 warning in 74.59s**. '
        'The warning is the existing Starlette HTTPX TestClient deprecation. All existing 252 tests plus '
        '27 new focused tests passed: format/partial IDs, malformed/valid emails, phone amounts/codes, '
        'names/institutions, confidence/review preservation, contextual duplicates, scoring/FP/FN/F1, '
        'split reproducibility/version, and private feedback export. Existing tests cover all file formats, '
        'redaction, audit replay, feedback, artifacts, pipeline and local API.',
        '\nAn initial detector-only run had 65 passed / 1 failed because the context-observation test '
        'wrapper did not accept the new optional exact-offset keyword. The wrapper now forwards it; '
        'the original context-bound assertion is retained and the full suite passes. '
        '`node --test tests/frontend/core.test.mjs`: **4 passed / 0 failed**; '
        '`node --check app/web/static/app.mjs`: exit 0. Frontend source was not modified.',
        '\nExact evaluation/diagnostic commands, in execution order:',
        '\n```powershell\n.venv/Scripts/python.exe tools/build_detector_dataset.py\n'
        '.venv/Scripts/python.exe tools/evaluate_detector.py --output detector_eval_baseline.json\n'
        '.venv/Scripts/python.exe -u tools/compare_detector_documents.py --stage baseline\n'
        '# Detector hardening occurred only after both baselines completed.\n'
        '.venv/Scripts/python.exe tools/evaluate_detector.py --split development --output detector_eval_development.json\n'
        '.venv/Scripts/python.exe -m pytest tests/test_pii_detection.py -q\n'
        '# Final employee boundaries and context test adapter were completed; policy frozen.\n'
        '.venv/Scripts/python.exe -m pytest tests -q\n'
        '.venv/Scripts/python.exe tools/evaluate_detector.py --output detector_eval_hardened.json\n'
        '.venv/Scripts/python.exe -u tools/compare_detector_documents.py --stage hardened\n'
        '.venv/Scripts/python.exe tools/export_reviewer_feedback.py --audit-store .private_review_app/audits --document-id 5180622d14f4c11743c86aa339e7166ce2e3d9db7211bb39d53db7f7b251cd63 --output-directory .private_feedback/phase10a-demo --detector-version 1.0 --source-category demonstration\n'
        '.venv/Scripts/python.exe tools/inspect_detector_comparison.py\n'
        'node --test tests/frontend/core.test.mjs\n'
        'node --check app/web/static/app.mjs\n'
        '.venv/Scripts/python.exe tools/write_phase10a_report.py\n```',
        f"\nEvaluation runtimes: baseline {baseline['elapsed_seconds']:.6f}s; "
        f"hardened {final['elapsed_seconds']:.6f}s (single analyzer per evaluation, no model reload per candidate). "
        'The JSON source fingerprints, dataset SHA and per-case decisions identify the saved runs. '
        'Baseline commands describe historical execution; they should not be rerun against hardened '
        'code to recreate policy 1.0. Current evaluation is repeatable with a fresh output filename; '
        'baseline metrics can be recomputed from its saved predictions. Real tools refuse overwrite and '
        'source-integrity mismatches.',
        '\n## M. Remaining Weaknesses',
        '\nThis is a synthetic, template-heavy evaluation with a small held-out set and no independently '
        'labeled real-document ground truth. OCR-concatenated names are often not proposed by Presidio, '
        'so post-validation cannot recover them. Two-capitalized-word projects may still confirm as PERSON. '
        'Institutional suffix rules can misclassify unusual personal names/contaminated spans and require '
        'broader human labeling. Missing contexts for bank/license candidates remain REVIEW; score alone '
        'does not justify rejecting them. No positive ground truth covers every supported identifier type. '
        'An application process already running before these file edits must be restarted to load policy '
        '1.1; this phase does not discard live reviewer sessions by restarting it automatically. '
        'Email partial-span gating can increase unredacted pending findings, as the actual PDF shows. '
        'Exact matching penalizes boundary errors rather than hiding them with fuzzy matches.',
        '\n## N. Completion Status',
        '\n**Implementation and evaluation completed.** Reproducible labeled evaluation, saved baseline, '
        'versioned deterministic hardening, frozen-policy held-out results, three-format private diagnostic '
        'comparison and explicit offline feedback export are present; all product regression tests pass. '
        'Synthetic success criteria are met: precision/F1 improve, recall is unchanged, and reviewed '
        'non-gold spans decrease without discarding reviewed gold spans. '
        '**Real-document REVIEW reduction was not achieved**, and an email-related residual warning '
        'increased; this limitation is reported rather than optimized away. Technical integration success '
        'does not establish real detection accuracy, complete PII coverage or readiness for downstream '
        'LLM submission. No frontend redesign, LLM, cloud API, automatic learning, real-review changes, '
        'commit or push was introduced.']
    (ROOT/'PHASE10A_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('PHASE10A_REPORT.md generated from saved measurements.')


if __name__=='__main__': main()

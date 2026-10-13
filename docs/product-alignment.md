# Product alignment

## Current contract — 2026-10-13

Local employee chat, one static manager page, no auth or LLM. Full files and original chat remain local. Only affected snippets/crops, filename/time, counts and decisions go to the manager service. Pending downloads and manager outages remain allowed; explicit denial blocks them. Actual engine processing failures block artifact access. Uncertain PII/faces are masked by default and remain reviewable; false-positive feedback can restore them.

The interface keeps SF Pro, grayscale, dark mode, larger headings, the approved SVG/send arrow, small Strands loading, restrained springs/reduced motion, previews and the teammate's graphs/diagrams.

## Locally verified

- Mixed PDFs receive OCR even with selectable text/page numbers. OCR uses original embedded pixels and verified transforms to the output raster.
- Embedded PNG/JPEG text in DOCX/PPTX, standalone PNG/JPEG, scanned and native PDFs all reach actual detection and destructive artifact redaction.
- Labeled passwords/account lists, addresses, DOB/MAC/IP, employee IDs and reserved-domain mailboxes are covered alongside Presidio/spaCy recognizers. Explicit introductions use spaCy token matching; OCR spacing maps classifier spans back to original offsets.
- Repeated sensitive values/crossing spans are protected. Saved PDFs receive bounded independent OCR residual checks; surviving regions are masked with original-source evidence, then rechecked. Failure is explicit.
- 24 supported demo files processed without mapping/verification errors. Tests also re-OCR returned artifacts and exercise saved-PDF leak repair and verifier failure. Final counts/evidence are in `review-2026-10-13.md`.
- Manager original/returned comparisons, rules, decisions and local-only files are verified locally. PDFs and Office raster images have real clickable previews.

## Honest limits

This establishes the tested fixtures and recognized PII, not universal detection. OCR/NER can miss unknown PII; uncertain findings and conservative coarse image masks require review. Unsupported legacy DOC, TXT file uploads, TIFF/GIF/vector images, embedded objects and complex unsupported Office structures are not complete coverage. Typed text remains supported. Native Office layout/vector/smart-art rendering is not implemented.

Built-in per-rule toggles remain absent; custom exact/regex redaction is implemented, with validation/timeouts. Block actions are rejected. Hosted manager/PostgreSQL promotion remains unverified in this task; local Vercel TLS validation failed and was not bypassed. Production/main differs from this local `pseudofix` work. Network interception, complete hosted samples and the finished project presentation remain outstanding.

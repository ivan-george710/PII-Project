# Cadence PII Guard

A document processing and PII protection pipeline for the Cadence case study.

The system is designed to process organizational evidence artifacts, extract their
content, identify sensitive information, and produce a safe artifact
that can be passed to an AI/LLM system.

---

# Project Architecture

The overall pipeline is:

```
Input File
    |
    v
[1. File Intelligence]
    |
    v
[2. Extraction + OCR]
    |
    v
[3. PII Detection]
    |
    v
[4. Redaction]
    |
    v
[5. Audit / Traceability]
    |
    v
Safe Artifact
    |
    v
LLM
```

## Engine Responsibilities

### Engine 1 — File Intelligence
STATUS: COMPLETE

Responsible for determining:
- What type of file was uploaded
- Whether the file is supported
- What extraction strategy should be used
- Whether a PDF is text-based, scanned, or hybrid
- Page-level PDF characteristics

---

### Engine 2 — Extraction + OCR
STATUS: COMPLETE

Engine 2 hides the extraction implementation from downstream modules.
Caller interface: `ExtractionEngine().extract(file_path)`

---

### Engine 3 — PII Detection
STATUS: STARTED / HANDOFF

Presidio Analyzer, spaCy NLP, and custom Cadence recognizers (`EMPLOYEE_ID`).

---

### Engine 4 — Redaction
STATUS: NOT STARTED

Expected responsibility:
- Take validated PII detections
- Replace or redact sensitive values
- Preserve document structure as much as possible
- Maintain traceability between original and redacted content
- Produce an artifact safe for downstream AI processing

---

### Engine 5 — Audit / Traceability
STATUS: COMPLETE

Engine 5 consumes processing results and produces tamper-evident audit records (`DocumentAuditRecord`):
- **WHAT**: entity type, confidence, recognizer
- **WHERE**: source file, page number, character offsets, OCR block, bounding box
- **HOW**: extraction method (pypdf / OCR / hybrid)
- **WHAT ACTION**: redaction action, replacement token, or rejected candidate with reason
- **WHEN & WHO**: UTC ISO 8601 timestamp, pipeline version, original file SHA-256
- **Zero Raw PII Guarantee**: Values are never stored raw; pseudonymized via HMAC-SHA256 (`AUDIT_HMAC_KEY`) with masked previews.
- **Tamper Evidence**: Cryptographic hash chaining over all entries and record verification (`verify_record`).

---

# Current Development Status

| Engine | Status |
|---|---|
| File Intelligence | COMPLETE |
| Extraction + OCR | COMPLETE |
| PII Detection | STARTED |
| Redaction | NOT STARTED |
| Audit / Traceability | COMPLETE |
| End-to-End Pipeline | NOT STARTED |
| Demo UI | NOT STARTED |

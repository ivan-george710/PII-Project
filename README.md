# Cadence PII Guard

The approved implementation plan is in [docs/issues/index.md](docs/issues/index.md). Directory indexes assign exact files to the five issues; the prototype notes below describe the existing reference implementation.


## Live CI/CD baseline

- Frontend: [PII Guard](https://pii-guard-mu.vercel.app)
- Backend API: [API documentation](https://pii-guard-mu.vercel.app/api/docs)
- Health endpoint: [API health](https://pii-guard-mu.vercel.app/api/health)
- Verified GitHub Actions run: [build, test, deploy, live smoke check](https://github.com/ivan-george710/PII-Project/actions/runs/37750508093)

Both services deploy together from GitHub Actions. Main pushes deploy production; other branch pushes deploy previews. The current production app remains the connectivity baseline. This draft branch adds WorkOS authentication and company setup; see [setup instructions](docs/local-setup.md). See [CI/CD details](docs/cicd.md). Vercel deployment protection may require sign-in.


A document processing and PII protection pipeline for the Cadence case study.

The system is designed to process organizational evidence artifacts, extract their
content, identify sensitive information, and eventually produce a safe artifact
that can be passed to an AI/LLM system.

---

# Project Architecture

The overall pipeline is:

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


## Engine Responsibilities

### Engine 1 — File Intelligence
STATUS: COMPLETE

Responsible for determining:

- What type of file was uploaded
- Whether the file is supported
- What extraction strategy should be used
- Whether a PDF is text-based, scanned, or hybrid
- Page-level PDF characteristics

Supported file types currently include:

- PDF
- DOCX
- PPTX
- PNG
- JPEG

For PDFs, the engine determines whether extraction should use:

- Text extraction
- OCR
- Hybrid extraction

The engine uses content-based MIME detection rather than trusting
the file extension.

---

### Engine 2 — Extraction + OCR
STATUS: COMPLETE

Engine 2 hides the extraction implementation from downstream modules.

The caller only needs to use:

    ExtractionEngine().extract(file_path)

The engine automatically determines the appropriate extraction strategy
using Engine 1.

Current extraction paths:

    Text PDF
        |
        v
    pypdf

    Scanned PDF
        |
        v
    PDF rendering
        |
        v
    RapidOCR / ONNX Runtime

    Hybrid PDF
        |
        +--> text page --> pypdf
        |
        +--> image page --> OCR

Extraction results are represented using:

    ExtractionResult
        |
        +-- pages[]
              |
              +-- page_number
              +-- text
              +-- extraction_method
              +-- OCR blocks (when applicable)

OCR blocks additionally preserve:

- OCR text
- OCR confidence
- Bounding box

This information is intentionally preserved because downstream
PII detection, redaction, and audit functionality will need source
traceability.

---

# Engine 3 — PII Detection
STATUS: STARTED / HANDOFF

This engine has been started but is NOT COMPLETE.

The current implementation uses:

    Presidio Analyzer
          |
          +-- spaCy NLP
          |
          +-- Presidio recognizers
          |
          +-- Custom Cadence recognizers

The first custom recognizer currently implemented is:

    EMPLOYEE_ID

Example:

    EMP-38104
    EMP-40522

The current PII detection module can already:

- Analyze ExtractionResult objects
- Run Presidio analysis
- Use spaCy-based PERSON detection
- Use Presidio pattern recognizers
- Detect Cadence employee IDs
- Return page-level PII detections
- Preserve recognizer and confidence information
- Separate confirmed candidates from rejected entity types

However, Engine 3 still requires substantial work.

Known issues from testing against the Cadence Risk Management Policy include:

- False-positive PERSON detections
- Low-confidence PHONE_NUMBER detections
- False-positive US_DRIVER_LICENSE detections
- False-positive US_BANK_NUMBER detections
- OCR/NLP boundary problems
- Overlapping recognizer results
- Entity-specific confidence handling
- Context-aware validation
- Government ID detection/classification
- More Cadence-specific recognizers
- Better source-block mapping

DO NOT consider the current Presidio output production-ready.

The goal is NOT simply:

    "Run Presidio and redact everything it detects."

Presidio is being used as the detection framework. The application
needs its own validation and classification layer to determine which
Presidio candidates actually constitute PII under the Cadence policy.

---

# Engine 4 — Redaction
STATUS: NOT STARTED

Expected responsibility:

- Take validated PII detections
- Replace or redact sensitive values
- Preserve document structure as much as possible
- Maintain traceability between original and redacted content
- Produce an artifact safe for downstream AI processing

---

# Engine 5 — Audit / Traceability
STATUS: NOT STARTED

Expected responsibility:

- Record what was detected
- Record where it was detected
- Record how it was detected
- Record redaction actions
- Preserve source/page/block relationships
- Support internal audit requirements

---

# Current Repository Structure

    cadence-pii-guard/
    |
    +-- app/
    |   |
    |   +-- engines/
    |       |
    |       +-- file_intelligence/
    |       |
    |       +-- extraction/
    |       |
    |       +-- pii_detection/
    |       |
    |       +-- redaction/
    |       |
    |       +-- audit/
    |
    +-- tests/
    |   |
    |   +-- fixtures/
    |
    +-- sample_documents/
    |
    +-- output/
    |
    +-- requirements.txt
    +-- README.md
    +-- .gitignore
    +-- run.py


# Important Development Principle

Each engine should have a clear contract with the next engine.

Engine 1 produces:

    FileMetadata

Engine 2 consumes the file and produces:

    ExtractionResult

Engine 3 should consume:

    ExtractionResult

and produce:

    PIIDetectionResult

Engine 4 should consume validated PII detections and produce:

    Redacted Artifact

Engine 5 should consume the processing results and produce:

    Audit / Traceability information


Do not tightly couple downstream engines to the implementation details
of previous engines.

---

# Testing

Run the complete test suite with:

    python -m pytest -v

The project uses the active Python virtual environment.

Recommended:

    .venv\Scripts\activate

Then:

    python -m pytest -v


# Current Development Status

| Engine | Status |
|---|---|
| File Intelligence | COMPLETE |
| Extraction + OCR | COMPLETE |
| PII Detection | STARTED |
| Redaction | NOT STARTED |
| Audit / Traceability | NOT STARTED |
| End-to-End Pipeline | NOT STARTED |
| Demo UI | NOT STARTED |

---

# Working on Engine 3

Start by reviewing:

    app/engines/pii_detection/

The current implementation is a starting point, not a finished solution.

The important architectural boundary is:

    ExtractionResult
          |
          v
    PIIDetectionEngine
          |
          v
    PIIDetectionResult

Engine 3 should improve detection quality without requiring changes
to the completed extraction engine unless a concrete extraction defect
is discovered.

Before changing Engine 1 or Engine 2, verify whether the issue is
actually an extraction problem or a downstream detection problem.

---

# Case Study Goal

The final system should provide a repeatable pipeline for:

1. Accepting organizational evidence artifacts
2. Determining their structure
3. Extracting text while preserving source context
4. Detecting and classifying PII
5. Redacting PII
6. Maintaining traceability
7. Producing a safe artifact for downstream AI processing

The system should prioritize high PII coverage while minimizing
false positives and preserving the original document's structure
and context.

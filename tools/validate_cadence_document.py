"""Run deterministic detection/redaction, reusing trusted OCR when available.

Sensitive artifacts belong in the existing ACL-restricted .private_validation
directory. Historical extraction and results are never overwritten.
"""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".private_validation"
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def restore_extraction(data):
    from app.engines.extraction.models import ExtractionResult, ExtractedPage, OCRTextBlock
    return ExtractionResult(Path(data["source_path"]), data["filename"], data["file_type"], [
        ExtractedPage(p["page_number"], p["text"], p["extraction_method"],
                      [OCRTextBlock(**b) for b in p["blocks"]] if p["blocks"] is not None else None)
        for p in data["pages"]])


def restore_detection(data):
    """Read current or historical audit records without using legacy adjudication."""
    from app.engines.pii_detection.models import PIIDetectionResult, DetectedPII
    return PIIDetectionResult(Path(data["source_path"]), data["filename"],
        [DetectedPII(**d) for d in data["detections"]], [DetectedPII(**d) for d in data["rejected"]],
        [DetectedPII(**d) for d in data.get("review", [])], data.get("raw_candidate_count", 0),
        data.get("pages_analyzed", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cached-extraction", "--diagnostics-only", action="store_true",
                        help="Require trusted cached extraction; never run OCR")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if not PRIVATE.is_dir():
        raise RuntimeError("Prepare an access-restricted .private_validation directory before running")
    sources = list(ROOT.glob("*.pdf"))
    if len(sources) != 1:
        raise RuntimeError("Expected exactly one root PDF; select source before running")
    source = sources[0]
    source_hash = digest(source)
    historical = PRIVATE / source_hash[:16]
    destination = PRIVATE / (source_hash[:16] + "-deterministic")
    destination.mkdir(exist_ok=True)
    started = perf_counter()
    from app.engines.file_intelligence import FileIntelligenceEngine
    from app.engines.pii_detection import PIIDetectionEngine
    from app.engines.redaction import RedactionEngine, RedactionValidationError
    from app.engines.extraction import ExtractionEngine

    metadata = FileIntelligenceEngine().analyze(str(source))
    fingerprints = {str(p.relative_to(ROOT)): digest(p)
                    for p in sorted((ROOT / "app" / "engines").rglob("*.py"))}
    cached_path = historical / "extraction.json"
    reused = cached_path.is_file()
    if reused:
        manifest = read(historical / "manifest.json")
        if manifest["source_sha256"] != source_hash:
            raise RuntimeError("Source fingerprint does not match cached extraction")
        upstream = {path: old_hash for path, old_hash in manifest["engine_code_sha256"].items()
                    if path.replace("\\", "/").startswith(
                        ("app/engines/extraction/", "app/engines/file_intelligence/"))}
        if not upstream:
            raise RuntimeError("Trusted extraction implementation fingerprints are missing")
        for path, old_hash in upstream.items():
            if digest(ROOT / path) != old_hash:
                raise RuntimeError("Extraction implementation differs from trusted cache")
        extraction = restore_extraction(read(cached_path))
    else:
        if args.cached_extraction:
            raise RuntimeError("Trusted extraction cache is unavailable; OCR was not run")
        # The restricted directory also holds transient rendered images.
        import os
        import tempfile
        from contextlib import redirect_stdout
        temporary = destination / "temp"
        temporary.mkdir(exist_ok=True)
        tempfile.tempdir = str(temporary)
        os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
        with (destination / "extraction_progress.log").open("w", encoding="utf-8") as log:
            with redirect_stdout(log):
                extraction = ExtractionEngine().extract(source)
        save(destination / "extraction.json", asdict(extraction))
    if Path(extraction.source_path).resolve() != source.resolve():
        raise RuntimeError("Cached extraction belongs to a different source path")
    initialization_started = perf_counter()
    engine = PIIDetectionEngine()
    initialization_seconds = perf_counter() - initialization_started
    detection_started = perf_counter()
    detection = engine.detect(extraction)
    detection_seconds = perf_counter() - detection_started
    redaction_started = perf_counter()
    redaction = RedactionEngine().redact(extraction, detection)
    redaction_seconds = perf_counter() - redaction_started
    blocked = False
    try:
        redaction.to_text_payload()
    except RedactionValidationError:
        blocked = True
    breakdown = defaultdict(Counter)
    for disposition, records in (("confirmed", detection.detections), ("rejected", detection.rejected),
                                 ("review", detection.review)):
        for record in records:
            breakdown[record.entity_type][disposition] += 1
    records = detection.detections + detection.rejected + detection.review
    summary = {
        "source_sha256": source_hash,
        "architecture": "presidio_and_deterministic_validation",
        "extraction_cache_reused": reused,
        "ocr_rerun": not reused,
        "pages": len(extraction.pages),
        "extracted_characters": sum(len(p.text) for p in extraction.pages),
        "ocr_blocks": sum(len(p.blocks or []) for p in extraction.pages),
        "detection": detection.diagnostics,
        "accounting_consistent": detection.disposition_count == detection.raw_candidate_count,
        "entity_breakdown": {entity: dict(counts) for entity, counts in sorted(breakdown.items())},
        "deprecated_adjudication_fields_unset": all(d.llm_decision is None and d.llm_reason is None for d in records),
        "applied_redactions": redaction.applied_redaction_count,
        "redaction_issues": dict(Counter(issue.code for issue in redaction.issues)),
        "redaction_complete": redaction.redaction_complete,
        "safe_for_llm": redaction.safe_for_llm,
        "text_export_blocked": blocked,
        "timings": {"initialization_seconds": initialization_seconds,
                    "detection_seconds": detection_seconds, "redaction_seconds": redaction_seconds,
                    "total_seconds": perf_counter() - started},
    }
    save(destination / "manifest.json", {"source_sha256": source_hash, "engine_code_sha256": fingerprints,
                                       "extraction_cache": str(cached_path) if reused else None})
    save(destination / "detections.json", asdict(detection))
    save(destination / "redaction_internal.json", asdict(redaction))
    (destination / "redacted_internal_review.txt").write_text(redaction.full_text, encoding="utf-8")
    save(destination / "deterministic_metrics.json", summary)
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Avoid accidental sensitive text from vendor exception messages.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None

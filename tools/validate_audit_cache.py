"""Audit existing trusted caches; no OCR, detector execution or reviewer overrides."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    started = perf_counter()
    from tools.validate_cadence_document import restore_extraction, restore_detection
    from app.engines.redaction.models import RedactionResult, RedactedPage, RedactionRecord, RedactionIssue
    from app.engines.pii_detection.models import DetectedPII
    from app.engines.audit import AuditEngine
    private = ROOT / ".private_validation"
    available = list(private.glob("*-deterministic/deterministic_metrics.json"))
    if len(available) != 1:
        raise RuntimeError("Expected one deterministic cached diagnostic")
    current = available[0].parent
    old = private / current.name.removesuffix("-deterministic")
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    metrics = read(available[0])
    source = list(ROOT.glob("*.pdf"))
    if len(source) != 1 or hashlib.sha256(source[0].read_bytes()).hexdigest() != metrics["source_sha256"]:
        raise RuntimeError("Cached source fingerprint mismatch")
    extraction = restore_extraction(read(old / "extraction.json"))
    detection = restore_detection(read(current / "detections.json"))
    data = read(current / "redaction_internal.json")
    redaction = RedactionResult(Path(data["source_path"]), data["filename"],
        [RedactedPage(**p) for p in data["pages"]], [RedactionRecord(**r) for r in data["redactions"]],
        {tag: [DetectedPII(**d) for d in records] for tag, records in data["tag_mapping"].items()},
        [RedactionIssue(i["code"], i["page_number"], DetectedPII(**i["detection"]), i["blocking"],
                        DetectedPII(**i["superseded_by"]) if i["superseded_by"] else None) for i in data["issues"]],
        [DetectedPII(**d) for d in data["rejected"]])
    before = asdict(detection)
    engine = AuditEngine()
    audit = engine.create_audit(extraction, detection, redaction)
    # An unchanged diagnostic may refresh schema-derived metadata at the same
    # revision, but it must not replace a snapshot containing reviewer changes.
    existing = engine.store.directory / ("audit_" + audit.document_id + ".json")
    expected = None
    if existing.exists():
        saved = read(existing)
        if saved["revision"] != 0 or saved["feedback"]:
            raise RuntimeError("Existing audit contains reviewer corrections; diagnostic will not overwrite it")
        expected = 0
    path = engine.save_audit(audit, expected_revision=expected)
    loaded = engine.load_audit(audit.document_id)
    summary = audit.sanitized_summary() | {"records": len(audit.records),
        "all_automated_candidates_accounted": len(audit.records) == detection.raw_candidate_count,
        "reload_matches": loaded == audit, "original_detection_unchanged": before == asdict(detection),
        "ocr_rerun": False, "detection_rerun": False, "feedback_applied": False,
        "elapsed_seconds": round(perf_counter() - started, 3)}
    path.with_name("cadence_sanitized_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None

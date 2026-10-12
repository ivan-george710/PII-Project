"""Real local Office evaluation; print counts only, retain sensitive evidence privately."""
from pathlib import Path
from dataclasses import asdict
import argparse
import json
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from app.pipeline import DocumentPipeline
    from app.engines.audit.storage import AuditStore
    from app.engines.extraction.office import source_hash
    started = perf_counter()
    store = AuditStore(ROOT / ".private_artifacts")
    store._prepare()
    pipeline = DocumentPipeline(artifact_output_dir=store.directory)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["docx", "pptx"], help="Evaluate just one format; retain other saved metrics")
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    private = read(store.directory / "phase7_diagnostic_internal.json") if args.format else {}
    public = read(store.directory / "phase7_summary.json") if args.format else {}
    for kind in ([args.format] if args.format else ["docx", "pptx"]):
        paths = list(ROOT.glob("Cadence_*." + kind))
        if not paths:
            public[kind] = {"available": False}
            continue
        if len(paths) != 1:
            raise ValueError("Expected one supplied document per format")
        path = paths[0]
        before = source_hash(path)
        result = pipeline.process(path)
        summary = result.sanitized_summary()
        extraction = result.extraction_result
        summary["extracted_characters"] = sum(len(p.text) for p in extraction.pages) if extraction else 0
        summary["mapped_segments"] = len(extraction.structure.segments) if extraction and extraction.structure else 0
        summary["nonempty_sections_or_slides"] = sum(bool(p.text.strip()) for p in extraction.pages) if extraction else 0
        summary["original_unchanged"] = before == source_hash(path)
        summary["available"] = True
        public[kind] = summary
        private[kind] = {"source_path": str(path), "source_sha256": before,
                         "artifact_path": str(result.artifact_result.path) if result.artifact_result and result.artifact_result.path else None,
                         "mapping_issues": [asdict(i) for i in result.artifact_result.mapping_issues] if result.artifact_result else [],
                         "summary": summary}
        print(json.dumps({"format": kind, "diagnostic": summary}, sort_keys=True), flush=True)
    store._atomic(store.directory / "phase7_diagnostic_internal.json", private)
    store._atomic(store.directory / "phase7_summary.json", public)
    print(json.dumps({"total_diagnostic_seconds": round(perf_counter() - started, 6)}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({"status": "failed", "message": "Local diagnostic failed; inspect private state."}))
        raise SystemExit(1) from None

"""Targeted local three-format validation; PDF uses trusted extraction/detection caches."""
from dataclasses import asdict
import json
import argparse
from pathlib import Path
import sys
from types import SimpleNamespace
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from app.pipeline import DocumentPipeline
    from app.engines.extraction.models import PDFSourceMap
    from app.engines.extraction.office import source_hash
    from app.engines.audit.storage import AuditStore
    from tools.validate_cadence_document import restore_extraction,restore_detection
    started=perf_counter()
    store=AuditStore(ROOT/".private_artifacts")
    store._prepare()
    read=lambda path:json.loads(path.read_text(encoding="utf-8"))
    office=DocumentPipeline(artifact_output_dir=store.directory)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format",choices=["pdf","docx","pptx"])
    args=parser.parse_args()
    summaries=read(store.directory/"phase8_summary.json") if args.format and (store.directory/"phase8_summary.json").exists() else {}
    internal=read(store.directory/"phase8_diagnostic_internal.json") if args.format and (store.directory/"phase8_diagnostic_internal.json").exists() else {}
    for kind in ([args.format] if args.format else ["pdf","docx","pptx"]):
        paths=list(ROOT.glob("Cadence_*."+kind))
        if not paths:
            summaries[kind]={"available":False}
            continue
        if len(paths)!=1: raise ValueError("Ambiguous supplied document")
        source=paths[0]
        before=source_hash(source)
        if kind=="pdf":
            metrics_files=list((ROOT/".private_validation").glob("*-deterministic/deterministic_metrics.json"))
            if len(metrics_files)!=1: raise ValueError("Trusted cache not uniquely available")
            current=metrics_files[0].parent
            metrics=read(metrics_files[0])
            if metrics["source_sha256"]!=before: raise ValueError("PDF cache source integrity mismatch")
            manifest=read(current/"manifest.json")
            if manifest["source_sha256"]!=before: raise ValueError("PDF cached manifest differs")
            import hashlib
            for name,digest in manifest["engine_code_sha256"].items():
                normalized=name.replace("\\","/")
                if normalized.startswith("app/engines/pii_detection/"):
                    if hashlib.sha256((ROOT/normalized).read_bytes()).hexdigest()!=digest:
                        raise ValueError("Detection cache policy fingerprint differs")
            historical=ROOT/".private_validation"/current.name.removesuffix("-deterministic")
            extraction=restore_extraction(read(historical/"extraction.json"))
            detection=restore_detection(read(current/"detections.json"))
            # The trusted prior diagnostic used the existing default 150-dpi OCR.
            # This additive metadata is attached in memory; cache files are untouched.
            extraction.pdf_source=PDFSourceMap(before,{str(p.page_number):150 for p in extraction.pages if p.extraction_method=="ocr"})
            pipeline=DocumentPipeline(extraction=SimpleNamespace(extract=lambda _:extraction),
                detection=SimpleNamespace(detect=lambda _:detection),artifact_output_dir=store.directory)
        else: pipeline=office
        print(json.dumps({"format":kind,"status":"processing"}),flush=True)
        result=pipeline.process(source)
        summary=result.sanitized_summary()
        summary["source_unchanged"]=source_hash(source)==before
        summary["source_locations"]=len(result.extraction_result.pages) if result.extraction_result else 0
        summary["cache_reused"]=kind=="pdf"
        summaries[kind]=summary
        internal[kind]={"source_path":str(source),"source_sha256":before,"summary":summary,
                        "artifact":asdict(result.artifact_result) if result.artifact_result else None}
        store._atomic(store.directory/"phase8_diagnostic_internal.json",internal)
        store._atomic(store.directory/"phase8_summary.json",summaries)
        print(json.dumps({"format":kind,"diagnostic":summary},sort_keys=True),flush=True)
    print(json.dumps({"elapsed_seconds":round(perf_counter()-started,6)}))


if __name__=="__main__":
    try: main()
    except Exception:
        print(json.dumps({"status":"failed","message":"Local validation failed; inspect private state."}))
        raise SystemExit(1) from None

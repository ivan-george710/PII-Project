"""Aggregate-only three-format visual diagnostic. PDF reuses trusted OCR/text caches."""
from dataclasses import asdict
from pathlib import Path
import json
import sys
from types import SimpleNamespace
from time import perf_counter
import hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    from app.pipeline import DocumentPipeline
    from app.engines.audit.storage import AuditStore
    from app.engines.extraction.office import source_hash
    from app.engines.extraction.models import PDFSourceMap
    from app.engines.visual_detection import VisualInspectionEngine
    from tools.validate_cadence_document import restore_extraction,restore_detection
    store=AuditStore(ROOT/'.private_phase11/real-documents');store._prepare()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    if (store.directory/'summary.json').exists():raise ValueError('Private diagnostic evidence already exists')
    started=perf_counter();visual=VisualInspectionEngine();summaries={}
    for kind in ['pdf','docx','pptx']:
        paths=list(ROOT.glob('Cadence_*.'+kind))
        if len(paths)!=1:raise ValueError('Source is not uniquely available')
        path=paths[0];digest=source_hash(path)
        if kind=='pdf':
            baseline=read(ROOT/'.private_detector_eval/pdf_baseline.json')
            hardened=read(ROOT/'.private_detector_eval/pdf_hardened.json')
            policy=read(ROOT/'detector_eval_hardened.json')['policy_fingerprint']
            if baseline['source_sha256']!=digest:raise ValueError('Untrusted original PDF cache')
            for name,expected in policy.items():
                if hashlib.sha256((ROOT/'app/engines/pii_detection'/name).read_bytes()).hexdigest()!=expected:raise ValueError('Text detector policy changed')
            extraction=restore_extraction(baseline['extraction'])
            extraction.pdf_source=PDFSourceMap(digest,{str(p.page_number):150 for p in extraction.pages if p.extraction_method=='ocr'})
            detection=restore_detection(hardened['detection'])
            pipeline=DocumentPipeline(extraction=SimpleNamespace(extract=lambda _:extraction),
                detection=SimpleNamespace(detect=lambda _:detection),visual_detection=visual,
                artifact_output_dir=store.directory)
        else:pipeline=DocumentPipeline(visual_detection=visual,artifact_output_dir=store.directory)
        print(json.dumps({'format':kind,'status':'processing'}),flush=True)
        result=pipeline.process(path);public=result.sanitized_summary()
        public['ocr_reused']=kind=='pdf';public['text_detection_reused']=kind=='pdf'
        public['source_unchanged']=source_hash(path)==digest
        public['physical_locations']=len(result.extraction_result.pages) if result.extraction_result else 0
        summaries[kind]=public
        store._atomic(store.directory/(kind+'_internal.json'),dict(source_sha256=digest,
            extraction=asdict(result.extraction_result) if result.extraction_result else None,
            audit=asdict(result.audit_result) if result.audit_result else None,
            artifact=asdict(result.artifact_result) if result.artifact_result else None,summary=public))
        store._atomic(store.directory/'summary.json',summaries)
        print(json.dumps({'format':kind,'visual':public['visual_privacy'],'artifact':public['artifact'],
            'failure':public['failure'],'stage_seconds':public['stage_timings_seconds']}),flush=True)
        if result.failure:raise ValueError('Real visual diagnostic failed; private evidence retained')
    summaries['elapsed_seconds']=perf_counter()-started;store._atomic(store.directory/'summary.json',summaries)
    (ROOT/'phase11_visual_diagnostic.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    print(json.dumps({'elapsed_seconds':summaries['elapsed_seconds']}))


if __name__=='__main__':main()

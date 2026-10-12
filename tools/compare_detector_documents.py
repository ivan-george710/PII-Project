"""Private cached real-document decision comparison; no ground truth or overrides."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def candidates(result):
    return result.detections+result.rejected+result.review


def summary(result):
    return dict(raw=result.raw_candidate_count, confirmed=len(result.detections),
        rejected=len(result.rejected), review=len(result.review),
        accounting_consistent=result.disposition_count==result.raw_candidate_count,
        entities={e:dict(Counter(d.final_decision for d in candidates(result) if d.entity_type==e))
                  for e in sorted({d.entity_type for d in candidates(result)})},
        review_reasons=dict(Counter(d.validation_reason for d in result.review)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['baseline','hardened'],required=True)
    args=parser.parse_args()
    from app.engines.audit.storage import AuditStore
    from app.engines.extraction.office import source_hash
    from app.engines.pii_detection import PIIDetectionEngine
    from app.engines.pii_detection import validation
    from app.engines.extraction.docx import extract_docx
    from app.engines.extraction.pptx import extract_pptx
    from tools.validate_cadence_document import restore_extraction,restore_detection
    from tools.evaluate_detector import policy_fingerprint
    store=AuditStore(ROOT/'.private_detector_eval'); store._prepare()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    output=store.directory/(args.stage+'.json')
    if output.exists(): raise ValueError('Evidence already exists')
    started=perf_counter(); engine=PIIDetectionEngine(); report={}
    for kind in ['pdf','docx','pptx']:
        paths=list(ROOT.glob('Cadence_*.'+kind))
        if len(paths)!=1: raise ValueError('Supplied source is not unique')
        source=paths[0]; digest=source_hash(source)
        cache=store.directory/(kind+'_baseline.json')
        if args.stage=='baseline':
            if kind=='pdf':
                metrics=list((ROOT/'.private_validation').glob('*-deterministic/deterministic_metrics.json'))
                if len(metrics)!=1 or read(metrics[0])['source_sha256']!=digest:
                    raise ValueError('Untrusted OCR cache')
                directory=metrics[0].parent
                manifest=read(directory/'manifest.json')
                for name,h in manifest['engine_code_sha256'].items():
                    normalized=name.replace('\\','/')
                    if normalized.startswith('app/engines/pii_detection/') and hashlib.sha256((ROOT/normalized).read_bytes()).hexdigest()!=h:
                        raise ValueError('Historical detector differs before baseline')
                extraction=restore_extraction(read(directory.parent/directory.name.removesuffix('-deterministic')/'extraction.json'))
                old=restore_detection(read(directory/'detections.json'))
                elapsed=0; reused=True
            else:
                extraction={'docx':extract_docx,'pptx':extract_pptx}[kind](source)
                tick=perf_counter(); old=engine.detect(extraction); elapsed=perf_counter()-tick; reused=False
            store._atomic(cache,dict(source_sha256=digest,extraction=asdict(extraction),detection=asdict(old)))
            report[kind]=dict(summary=summary(old),seconds=elapsed,historical_detection_reused=reused)
        else:
            data=read(cache)
            if data['source_sha256']!=digest: raise ValueError('Source changed')
            extraction=restore_extraction(data['extraction'])
            # Historical helper predates Office structure; restore it separately.
            from app.engines.extraction.models import restore_structure
            extraction.structure=restore_structure(data['extraction'].get('structure'))
            old=restore_detection(data['detection'])
            tick=perf_counter(); new=engine.detect(extraction); elapsed=perf_counter()-tick
            def indexed(result):
                return {(d.page_number,d.start,d.end,d.entity_type,d.recognizer):d for d in candidates(result)}
            previous,current=indexed(old),indexed(new)
            changes=Counter()
            for k,d in current.items():
                before=previous[k].final_decision if k in previous else 'ABSENT'
                if before!=d.final_decision: changes[before+' -> '+d.final_decision]+=1
            for k in previous.keys()-current.keys(): changes[previous[k].final_decision+' -> ABSENT']+=1
            from app.engines.redaction import RedactionEngine
            redaction=RedactionEngine().redact(extraction,new)
            # Exact confirmed strings still present: diagnostic only, not ground truth.
            residuals=Counter(d.entity_type for d in new.detections
                if any(d.text in p.text for p in redaction.pages))
            report[kind]=dict(before=summary(old),after=summary(new),changes=dict(changes),
                seconds=elapsed,redaction_complete=redaction.redaction_complete,
                safe_for_llm=redaction.safe_for_llm,residual_confirmed_strings=dict(residuals))
            store._atomic(store.directory/(kind+'_hardened.json'),dict(detection=asdict(new),redaction=asdict(redaction)))
        if source_hash(source)!=digest: raise ValueError('Source modified')
        print(json.dumps({'format':kind,'completed':True}),flush=True)
    report.update(detector_policy_version=getattr(validation,'DETECTOR_POLICY_VERSION','1.0'),
                  policy_fingerprint=policy_fingerprint(),elapsed_seconds=perf_counter()-started)
    store._atomic(output,report)
    # Only aggregate diagnostics leave the private store.
    (ROOT/('detector_documents_'+args.stage+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'elapsed_seconds':report['elapsed_seconds']}))


if __name__=='__main__': main()

"""Post-run aggregate risk checks; reads private snapshots without re-running engines."""
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from app.engines.audit.storage import AuditStore
    from app.engines.redaction import RedactionEngine
    from tools.validate_cadence_document import restore_detection,restore_extraction
    from tools.compare_detector_documents import candidates
    store=AuditStore(ROOT/'.private_detector_eval'); store._prepare()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    report={}; evidence={}
    for kind in ['pdf','docx','pptx']:
        before=read(store.directory/(kind+'_baseline.json'))
        after=read(store.directory/(kind+'_hardened.json'))
        extraction=restore_extraction(before['extraction'])
        old=restore_detection(before['detection']); new=restore_detection(after['detection'])
        old_redaction=RedactionEngine().redact(extraction,old)
        new_redaction=RedactionEngine().redact(extraction,new)
        def residual(result,redacted):
            # Candidate instances with their literal value somewhere in any output
            # page, not unique strings or a ground-truth missed-PII count.
            return dict(Counter(d.entity_type for d in result.detections
                               if any(d.text in p.text for p in redacted.pages)))
        previous={(d.page_number,d.start,d.end,d.entity_type,d.recognizer):d for d in candidates(old)}
        changed=[]
        for d in candidates(new):
            prior=previous.get((d.page_number,d.start,d.end,d.entity_type,d.recognizer))
            if prior and prior.final_decision!=d.final_decision:
                text=next(p.text for p in extraction.pages if p.page_number==d.page_number)
                changed.append(dict(before=asdict(prior),after=asdict(d),
                    context=text[max(0,d.start-80):d.end+80]))
        evidence[kind]=changed
        report[kind]=dict(old_applied=old_redaction.applied_redaction_count,
            new_applied=new_redaction.applied_redaction_count,
            old_residual_confirmed_instances=residual(old,old_redaction),
            new_residual_confirmed_instances=residual(new,new_redaction),
            changed_reason_counts=dict(Counter(c['after']['validation_reason'] for c in changed)),
            old_blocking_issues=sum(i.blocking for i in old_redaction.issues),
            new_blocking_issues=sum(i.blocking for i in new_redaction.issues),
            known_risk='Not labeled; changed email is unresolved and no longer automatically redacted.' if kind=='pdf'
                       else 'Effective text redaction unchanged; unverified coverage remains.')
    store._atomic(store.directory/'changed_evidence.json',evidence)
    store._atomic(store.directory/'risk_checks.json',report)
    (ROOT/'detector_documents_risk_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__': main()

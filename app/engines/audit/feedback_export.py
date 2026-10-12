"""Explicit private offline curation export. Never mutates policy or audit state."""
from pathlib import Path

from .storage import AuditStore


def export_feedback(audit, *, directory=None, include_context=False,
                    detector_version="unknown-legacy", source_category="reviewed_document"):
    """Only actual feedback events are exported, not an unlabeled candidate inventory.

    Historical audits lack policy versions: do not silently stamp today's policy.
    Context opt-in permits plaintext PII inside the protected local directory.
    """
    from .engine import AuditEngine
    AuditEngine().get_review_queue(audit)  # Validate immutable baseline and event replay.
    if type(include_context) is not bool:
        raise ValueError('include_context must be an explicit boolean')
    if not isinstance(detector_version,str) or len(detector_version)>40:
        raise ValueError('Invalid detector version')
    if source_category not in {'reviewed_document','synthetic','demonstration','curated'}:
        raise ValueError('Invalid source category')
    store=AuditStore(directory if directory is not None else Path(__file__).resolve().parents[3]/'.private_feedback')
    store._prepare()
    records={r.detection_id:r for r in audit.records+audit.visual_records}
    pages={p.page_number:p.text for p in audit.extraction.pages}
    rows=[]
    for event in audit.feedback:
        r=records[event.detection_id]; d=r.original_detection
        row=dict(entity_type=d.entity_type,automated_decision=r.automated_decision,
            reviewer_decision=event.new_decision,reviewer_action=event.feedback.action.value
            if hasattr(event.feedback.action,'value') else event.feedback.action,
            recognizer=d.recognizer,detection_method=d.detection_method,confidence=d.confidence,
            source_format=audit.extraction.file_type,source_category=source_category,
            detector_policy_version=detector_version)
        if getattr(d,'category',None)=='BIOMETRIC':
            row['category']='BIOMETRIC'
            row['detector_policy_version']=audit.extraction.visual.policy_version
            # Never export crops/image payloads; optional context is text-only.
        elif include_context:
            text=pages[d.page_number]
            # <= 400 total code points even for a very large manually added span.
            start=max(0,d.start-120); end=min(len(text),start+400)
            row['context']=text[start:end]
            row['candidate_offsets_in_context']=[d.start-start,min(d.end,end)-start]
            row['candidate_truncated']=d.end>end
        rows.append(row)
    target=store.directory/'feedback_dataset.json'
    if target.is_symlink() or target.exists():
        raise ValueError('Export already exists or is a symlink; choose a new private directory')
    store._atomic(target,dict(schema_version=1,context_included=include_context,
                             requires_curation=True,examples=rows))
    return target

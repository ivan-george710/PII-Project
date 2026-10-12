"""Audit snapshots and explicit reviewer overrides; replacement stays in Engine 4."""
from collections import Counter, defaultdict, deque
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from app.engines.extraction.models import ExtractionResult, ExtractedPage, OCRTextBlock, restore_structure, PDFSourceMap
from app.engines.pii_detection.models import DetectedPII, PIIDetectionResult
from app.engines.redaction import RedactionEngine, RedactionValidationError
from .models import (AuditResult, AuditRecord, ReviewItem, ReviewerFeedback, FeedbackEvent,
                     ReviewAction, AuditValidationError, FeedbackConflictError, AuditStorageError)
from .storage import AuditStore


def _json(value):
    return json.dumps(value, default=str, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _key(detection):
    # Full record used only internally for unambiguous duplicate-occurrence matching.
    return _json(asdict(detection))


def _extraction_data(extraction):
    data = asdict(extraction)
    if data.get("structure") is None:
        data.pop("structure", None)  # Preserve historical PDF audit fingerprints/schema.
    if data.get("pdf_source") is None:
        data.pop("pdf_source", None)
    if data.get("visual") is None:
        data.pop("visual", None)
    return data


class AuditEngine:
    def __init__(self, storage_dir=None):
        self.store = AuditStore(storage_dir)
        self.redactor = RedactionEngine()

    def create_audit(self, extraction_result, detection_result, redaction_result) -> AuditResult:
        if extraction_result is None or detection_result is None or redaction_result is None:
            raise AuditValidationError("Extraction, detection and redaction results are required")
        extraction, detection, supplied = deepcopy((extraction_result, detection_result, redaction_result))
        if (type(detection.raw_candidate_count) is not int
                or detection.raw_candidate_count != detection.disposition_count):
            raise AuditValidationError("Raw candidate accounting is inconsistent")
        expected = self._redact(extraction, detection)
        if supplied != expected:
            raise AuditValidationError("Redaction result does not match the original inputs")
        doc = {"source_path": str(Path(extraction.source_path)),
               "filename": extraction.filename, "file_type": extraction.file_type,
               "pages": [asdict(p) for p in extraction.pages]}
        if extraction.structure is not None:
            doc["structure"] = asdict(extraction.structure)
        if extraction.pdf_source is not None:
            doc["pdf_source"] = asdict(extraction.pdf_source)
        if extraction.visual is not None:
            extraction.visual.validate()
            doc['visual'] = {k:v for k,v in asdict(extraction.visual).items() if k not in {'detection_seconds','cache_hits'}}
        document_id = _hash(doc)  # Internal only; never included in sanitized summaries.
        fingerprint = _hash([_extraction_data(extraction), asdict(detection), asdict(expected)])
        return self._build(document_id, extraction, detection, expected, [], fingerprint)

    def _redact(self, extraction, detection):
        try:
            return self.redactor.redact(extraction, detection)
        except (RedactionValidationError, TypeError, AttributeError, ValueError) as exc:
            raise AuditValidationError(f"Audit/redaction input validation failed ({type(exc).__name__})") from None

    @staticmethod
    def _initial_rows(original, extraction):
        page_order = {p.page_number: i for i, p in enumerate(extraction.pages)}
        rows = [(d, decision) for decision, records in (("CONFIRM", original.detections),
                 ("REJECT", original.rejected), ("REVIEW", original.review)) for d in records]
        indexed = list(enumerate(rows))
        indexed.sort(key=lambda pair: (page_order[pair[1][0].page_number], pair[1][0].start, pair[1][0].end,
                                       pair[1][0].entity_type, str(pair[1][0].recognizer), str(pair[1][0].detection_method)))
        from app.engines.visual_detection.audit import initial_visual_rows
        return [{"id": f"D{i:06d}", "original": deepcopy(d), "automated": decision,
                 "effective": deepcopy(d), "decision": decision, "corrected": False, "order": order}
                for i, (order, (d, decision)) in enumerate(indexed, 1)] + initial_visual_rows(extraction)

    @staticmethod
    def _human_detection(extraction, feedback):
        if type(feedback.page_number) is not int:
            raise AuditValidationError("Reviewer page number must be an integer")
        page = next((p for p in extraction.pages if p.page_number == feedback.page_number), None)
        if page is None:
            raise AuditValidationError("Reviewer page does not exist")
        start, end = feedback.original_start, feedback.original_end
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(page.text):
            raise AuditValidationError("Reviewer offsets are invalid")
        if not isinstance(feedback.entity_type, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", feedback.entity_type):
            raise AuditValidationError("Reviewer entity type is invalid")
        if feedback.entity_type in {'FACE','BIOMETRIC'}:
            raise AuditValidationError('Visual findings require image-region evidence, not text offsets')
        block = None
        if page.blocks and "\n".join(b.text for b in page.blocks) == page.text:
            cursor = 0
            for index, b in enumerate(page.blocks):
                if cursor <= start and end <= cursor + len(b.text):
                    block = index
                    break
                cursor += len(b.text) + 1
        return DetectedPII(feedback.entity_type, page.text[start:end], start, end, 0.0,
                           "human_review", "HumanReview", page.page_number, block,
                           "CONFIRM", "reviewer_identified_missed_pii", final_decision="CONFIRM")

    @staticmethod
    def _feedback(value):
        if not isinstance(value, ReviewerFeedback):
            raise AuditValidationError("Expected ReviewerFeedback")
        try:
            action = ReviewAction(value.action)
        except (ValueError, TypeError):
            raise AuditValidationError("Unsupported review action") from None
        if not isinstance(value.reviewer_id, str) or not value.reviewer_id.strip():
            raise AuditValidationError("Caller-supplied reviewer identifier is required")
        if value.reason is not None and not isinstance(value.reason, str):
            raise AuditValidationError("Reviewer reason must be text")
        if value.expected_decision is not None and (not isinstance(value.expected_decision, str)
                                                    or value.expected_decision not in {"CONFIRM", "REJECT", "REVIEW"}):
            raise AuditValidationError("Invalid expected decision")
        if value.timestamp is not None and (not isinstance(value.timestamp, str) or not value.timestamp):
            raise AuditValidationError("Timestamp must be timezone-aware ISO 8601")
        stamp = value.timestamp if value.timestamp is not None else datetime.now(timezone.utc).isoformat()
        try:
            instant = datetime.fromisoformat(stamp)
            if instant.tzinfo is None or instant.utcoffset() is None:
                raise ValueError()
        except (ValueError, TypeError):
            raise AuditValidationError("Timestamp must be timezone-aware ISO 8601") from None
        if action == ReviewAction.MISSED_PII:
            if value.detection_id is not None or value.expected_decision is not None:
                raise AuditValidationError("MISSED_PII uses source offsets, not an existing finding")
        elif (not isinstance(value.detection_id, str) or not re.fullmatch(r"[DHV]\d{6,}", value.detection_id)
              or any(v is not None for v in (value.page_number, value.original_start,
                                            value.original_end, value.entity_type))):
            raise AuditValidationError("Existing-finding feedback requires only its detection ID")
        return replace(value, action=action, timestamp=instant.astimezone(timezone.utc).isoformat())

    def _apply(self, rows, extraction, events, value):
        feedback = self._feedback(value)
        if feedback.action == ReviewAction.MISSED_PII:
            detection = self._human_detection(extraction, feedback)
            matching = [r for r in rows if not r.get('visual') and (r["effective"].page_number, r["effective"].start,
                        r["effective"].end, r["effective"].entity_type) ==
                        (detection.page_number, detection.start, detection.end, detection.entity_type)]
            if matching:
                target = matching[0]
                if target["automated"] is not None:
                    raise AuditValidationError("Finding already exists; review its detection ID")
            else:
                target = {"id": f"H{sum(r['automated'] is None for r in rows) + 1:06d}",
                          "original": detection, "automated": None, "effective": deepcopy(detection),
                          "decision": None, "corrected": False, "order": len(rows)}
                rows.append(target)
            new = "CONFIRM"
        else:
            target = next((r for r in rows if r["id"] == feedback.detection_id), None)
            if target is None:
                raise AuditValidationError("Detection identifier does not exist in this audit")
            new = "CONFIRM" if feedback.action == ReviewAction.CONFIRM_PII else "REJECT"
        previous = target["decision"]
        same = lambda f: (f.action, f.reviewer_id, f.detection_id, f.page_number, f.original_start,
                          f.original_end, f.entity_type, f.reason, f.expected_decision)
        if events and events[-1].detection_id == target["id"] and same(events[-1].feedback) == same(feedback):
            return None
        last = next((e for e in reversed(events) if e.detection_id == target["id"]), None)
        if last is not None and same(last.feedback) == same(feedback) and previous == new:
            return None
        if feedback.expected_decision is not None and feedback.expected_decision != previous:
            raise FeedbackConflictError("Expected decision is stale")
        if last is not None and previous != new and feedback.expected_decision is None:
            raise FeedbackConflictError("Conflicting correction requires the expected current decision")
        target["decision"] = new
        target["corrected"] = True
        # Original automated metadata is retained separately, not rewritten in place.
        metadata=dict(validation_decision=new, validation_reason='reviewer_override', final_decision=new)
        if not target.get('visual'):metadata.update(llm_decision=None,llm_reason=None)
        target["effective"] = replace(target["effective"], **metadata)
        return FeedbackEvent(f"F{len(events) + 1:06d}", target["id"], feedback, previous, new)

    def _build(self, document_id, extraction, original, baseline_redaction, events, fingerprint):
        rows = self._initial_rows(original, extraction)
        replayed = []
        for event in events:
            generated = self._apply(rows, extraction, replayed, event.feedback)
            if generated != event:
                raise AuditValidationError("Feedback history is inconsistent or contains duplicate events")
            replayed.append(generated)
        visual_rows=[r for r in rows if r.get('visual')]
        rows=[r for r in rows if not r.get('visual')]
        effective = PIIDetectionResult(extraction.source_path, extraction.filename, [], [], [],
                                       len(rows), list(original.pages_analyzed))
        for row in sorted(rows, key=lambda r: r["order"]):
            {"CONFIRM": effective.detections, "REJECT": effective.rejected,
             "REVIEW": effective.review}[row["decision"]].append(deepcopy(row["effective"]))
        redacted = self._redact(extraction, effective)
        records = [AuditRecord(r["id"], document_id, deepcopy(r["original"]), deepcopy(r["effective"]),
            r["automated"], r["decision"], "REJECTED" if r["decision"] == "REJECT" else "PENDING",
            extraction_method=next(p.extraction_method for p in extraction.pages
                                   if p.page_number == r["effective"].page_number), corrected=r["corrected"])
                   for r in rows]
        by_id = {r.detection_id: r for r in records}
        available = defaultdict(deque)
        for record in records:
            available[_key(record.effective_detection)].append(record.detection_id)
        applied = defaultdict(list)
        for tag, detections in redacted.tag_mapping.items():
            for d in detections:
                record = by_id[available[_key(d)].popleft()]
                record.redaction_status, record.tag = "APPLIED", tag
                applied[_key(d)].append(record)
                span = next(s for s in redacted.redactions if s.tag == tag and s.page_number == d.page_number
                            and s.original_start == d.start and s.original_end == d.end)
                record.redacted_start, record.redacted_end = span.redacted_start, span.redacted_end
        blocking = []
        for issue in redacted.issues:
            record = by_id[available[_key(issue.detection)].popleft()]
            if issue.code == "superseded_overlap":
                covering = applied[_key(issue.superseded_by)][0]
                record.redaction_status, record.tag = "SUPERSEDED", covering.tag
                record.superseded_by = covering.detection_id
                record.redacted_start, record.redacted_end = covering.redacted_start, covering.redacted_end
            else:
                record.redaction_status = {"review_required": "REVIEW_REQUIRED",
                    "unresolved_overlap": "UNRESOLVED_OVERLAP"}.get(issue.code, "VALIDATION_ISSUE")
                blocking.append((issue.code, record))
        if any(r.redaction_status == "PENDING" for r in records):
            raise AuditValidationError("Redaction traceability has unaccounted confirmed findings")
        queue = []
        overlap = sorted([r for code, r in blocking if code == "unresolved_overlap"],
                         key=lambda r: (r.effective_detection.page_number, r.effective_detection.start))
        groups = []
        for record in overlap:
            d = record.effective_detection
            if (not groups or groups[-1][0].effective_detection.page_number != d.page_number
                    or d.start >= max(r.effective_detection.end for r in groups[-1])):
                groups.append([record])
            else:
                groups[-1].append(record)
        for group in groups:
            ids = sorted(r.detection_id for r in group)
            queue.append(ReviewItem("overlap:" + ":".join(ids), "unresolved_overlap",
                group[0].effective_detection.page_number, ids, "Crossing spans lack a complete covering redaction."))
        for code, record in blocking:
            if code != "unresolved_overlap":
                queue.append(ReviewItem("finding:" + record.detection_id, code,
                    record.effective_detection.page_number, [record.detection_id],
                    "Human decision required." if code == "review_required" else "Decision metadata requires correction."))
        from app.engines.visual_detection.audit import VisualAuditRecord
        visual_records=[VisualAuditRecord(r['id'],document_id,deepcopy(r['original']),deepcopy(r['effective']),
            r['automated'],r['decision'],{'CONFIRM':'BLUR_REQUIRED','REJECT':'REJECTED','REVIEW':'REVIEW_REQUIRED'}[r['decision']],
            r['corrected']) for r in visual_rows]
        visual_result=deepcopy(extraction.visual)
        if visual_result is not None:
            visual_result.faces=[deepcopy(r.effective_detection) for r in visual_records]
            for r in visual_records:
                if r.effective_decision=='REVIEW':queue.append(ReviewItem('finding:'+r.detection_id,'visual_review',
                    r.effective_detection.page_number,[r.detection_id],'Human face privacy decision required.'))
            if visual_result.unsupported:queue.append(ReviewItem('visual:unsupported','unsupported_visual',1,[],
                'Visual content could not be fully inspected or mapped.'))
        queue.sort(key=lambda item: (item.page_number, item.item_id))
        counts = {"extracted_pages": len(extraction.pages), "raw_detection_count": original.raw_candidate_count,
                  "original_confirmed": len(original.detections), "original_rejected": len(original.rejected),
                  "original_review": len(original.review), "confirmed": len(effective.detections),
                  "rejected": len(effective.rejected), "review": len(effective.review),
                  "effective_finding_count": len(records), "human_added": sum(r.automated_decision is None for r in records),
                  "applied_redactions": redacted.applied_redaction_count,
                  "superseded_overlaps": sum(i.code == "superseded_overlap" for i in redacted.issues),
                  "unresolved_overlap_findings": len(overlap), "unresolved_overlap_groups": len(groups),
                  "blocking_issues": sum(i.blocking for i in redacted.issues), "review_queue_items": len(queue),
                  "feedback_events": len(events)}
        return AuditResult(document_id, deepcopy(extraction), deepcopy(original), deepcopy(baseline_redaction),
                           effective, redacted, records, queue, counts, deepcopy(events), len(events), fingerprint,
                           visual_records,visual_result)

    def _check(self, audit):
        if not isinstance(audit, AuditResult):
            raise AuditValidationError("Expected AuditResult")
        fingerprint = _hash([_extraction_data(audit.extraction), asdict(audit.original_detection_result),
                             asdict(audit.original_redaction_result)])
        if fingerprint != audit.baseline_fingerprint:
            raise AuditValidationError("Original audit snapshots were modified")
        initial = self.create_audit(audit.extraction, audit.original_detection_result, audit.original_redaction_result)
        rebuilt = self._build(initial.document_id, initial.extraction, initial.original_detection_result,
                              initial.original_redaction_result, audit.feedback, initial.baseline_fingerprint)
        if rebuilt != audit:
            raise AuditValidationError("Derived audit state or history was modified")
        return rebuilt

    def get_review_queue(self, audit):
        return deepcopy(self._check(audit).review_queue)

    def apply_feedback(self, audit, feedback) -> AuditResult:
        base = self._check(audit)
        rows = self._initial_rows(base.original_detection_result, base.extraction)
        replayed = []
        for event in base.feedback:
            generated = self._apply(rows, base.extraction, replayed, event.feedback)
            replayed.append(generated)
        event = self._apply(rows, base.extraction, replayed, feedback)
        if event is None:
            return base
        return self._build(base.document_id, base.extraction, base.original_detection_result,
                           base.original_redaction_result, [*base.feedback, event], base.baseline_fingerprint)

    def save_audit(self, audit, *, expected_revision=None):
        checked = self._check(audit)
        payload = {"schema_version": 1, "document_id": checked.document_id, "revision": checked.revision,
                   "extraction": _extraction_data(checked.extraction), "detection": asdict(checked.original_detection_result),
                   "feedback": [asdict(e) for e in checked.feedback],
                   "baseline_fingerprint": checked.baseline_fingerprint,
                   "baseline_redaction": asdict(checked.original_redaction_result),
                   "redaction": asdict(checked.redaction_result),
                   "records": [asdict(r) for r in checked.records],
                   "review_queue": [asdict(q) for q in checked.review_queue], "counts": checked.counts}
        if checked.visual_result is not None:
            payload['visual_records']=[asdict(r) for r in checked.visual_records]
        # One atomic snapshot includes inputs and all feedback. Derived views are rebuilt on load.
        return self.store.write(checked.document_id, payload, expected_revision)

    def load_audit(self, document_id):
        data = self.store.read(document_id)
        try:
            if data["schema_version"] != 1:
                raise AuditValidationError("Unsupported audit schema")
            source = data["extraction"]
            extraction = ExtractionResult(Path(source["source_path"]), source["filename"], source["file_type"], [
                ExtractedPage(p["page_number"], p["text"], p["extraction_method"],
                              [OCRTextBlock(**b) for b in p["blocks"]] if p["blocks"] is not None else None)
                for p in source["pages"]], restore_structure(source.get("structure")),
                PDFSourceMap(**source["pdf_source"]) if source.get("pdf_source") else None)
            from app.engines.visual_detection.models import restore_visual
            extraction.visual=restore_visual(source.get('visual'))
            d = data["detection"]
            detection = PIIDetectionResult(Path(d["source_path"]), d["filename"],
                [DetectedPII(**x) for x in d["detections"]], [DetectedPII(**x) for x in d["rejected"]],
                [DetectedPII(**x) for x in d["review"]], d["raw_candidate_count"], d["pages_analyzed"])
            initial = self.create_audit(extraction, detection, self._redact(extraction, detection))
            if initial.document_id != data["document_id"] or initial.document_id != document_id:
                raise AuditValidationError("Stored document fingerprint does not match")
            if (initial.baseline_fingerprint != data["baseline_fingerprint"]
                    or _json(asdict(initial.original_redaction_result)) != _json(data["baseline_redaction"])):
                raise AuditValidationError("Stored original redaction or baseline no longer matches")
            events = [FeedbackEvent(e["event_id"], e["detection_id"], ReviewerFeedback(**e["feedback"]),
                                    e["previous_decision"], e["new_decision"]) for e in data["feedback"]]
            result = self._build(initial.document_id, extraction, detection, initial.original_redaction_result,
                                 events, initial.baseline_fingerprint)
            if _json(data.get('visual_records',[]))!=_json([asdict(r) for r in result.visual_records]):
                raise AuditValidationError('Stored visual evidence differs from replayed state')
            if type(data["revision"]) is not int or result.revision != data["revision"]:
                raise AuditValidationError("Stored revision does not match feedback history")
            for saved, rebuilt in ((data["redaction"], asdict(result.redaction_result)),
                                   (data["records"], [asdict(r) for r in result.records]),
                                   (data["review_queue"], [asdict(q) for q in result.review_queue]),
                                   (data["counts"], result.counts)):
                if _json(saved) != _json(rebuilt):
                    raise AuditValidationError("Stored audit metadata does not match rebuilt state")
            return result
        except (AuditValidationError, AuditStorageError):
            raise
        except Exception as exc:
            raise AuditValidationError(f"Stored audit is invalid ({type(exc).__name__})") from None

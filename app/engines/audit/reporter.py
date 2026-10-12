"""Allowlisted summaries: no text, hashes, filenames, identities or free-form reasons."""
from collections import Counter
from .models import AuditValidationError

COUNT_FIELDS = {"extracted_pages", "raw_detection_count", "original_confirmed", "original_rejected",
                "original_review", "confirmed", "rejected", "review", "effective_finding_count", "human_added",
                "applied_redactions", "superseded_overlaps", "unresolved_overlap_findings",
                "unresolved_overlap_groups", "blocking_issues", "review_queue_items", "feedback_events"}
STATUSES = {"APPLIED", "REJECTED", "REVIEW_REQUIRED", "SUPERSEDED", "UNRESOLVED_OVERLAP", "VALIDATION_ISSUE"}
CATEGORIES = {"review_required", "unresolved_overlap", "unknown_decision", "visual_review", "unsupported_visual"}


def sanitized_summary(audit) -> dict:
    if (set(audit.counts) != COUNT_FIELDS or any(type(v) is not int or v < 0 for v in audit.counts.values())
            or type(audit.revision) is not int or audit.revision < 0):
        raise AuditValidationError("Malformed audit summary counts")
    return {"revision": audit.revision, "counts": {k: audit.counts[k] for k in sorted(COUNT_FIELDS)},
            "redaction_status_counts": dict(Counter(r.redaction_status if r.redaction_status in STATUSES else "INVALID"
                                                     for r in audit.records)),
            "review_category_counts": dict(Counter(q.category if q.category in CATEGORIES else "validation_issue"
                                                    for q in audit.review_queue)),
            "human_review_complete": audit.human_review_complete,
            "redaction_complete": audit.redaction_result.redaction_complete,
            "coverage_verified": audit.coverage_verified,
            "downstream_export_permitted": audit.downstream_export_permitted,
            "safe_for_llm": audit.safe_for_llm}

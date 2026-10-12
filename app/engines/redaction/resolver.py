"""Resolve contained spans; block crossing spans rather than expose their tails."""
from .models import RedactionIssue

PRIORITY = {"EMAIL_ADDRESS": 100, "US_SSN": 90, "CREDIT_CARD": 90,
            "EMPLOYEE_ID": 80, "PHONE_NUMBER": 70, "PERSON": 50, "URL": 10}


def resolve_overlaps(detections):
    ordered = sorted(enumerate(detections), key=lambda pair: (
        pair[1].start, pair[1].end, pair[0]))
    groups = []
    for _, detection in ordered:
        if not groups or detection.start >= max(d.end for d in groups[-1]):
            groups.append([detection])
        else:
            groups[-1].append(detection)
    selected, issues = [], []
    for group in groups:
        start, end = min(d.start for d in group), max(d.end for d in group)
        covering = [d for d in group if d.start == start and d.end == end]
        if not covering:
            issues.extend(RedactionIssue("unresolved_overlap", d.page_number, d)
                          for d in group)
            continue
        winner = max(covering, key=lambda d: (
            PRIORITY.get(d.entity_type, 0), d.confidence))
        selected.append(winner)
        issues.extend(RedactionIssue("superseded_overlap", d.page_number, d,
                                     False, winner)
                      for d in group if d is not winner)
    return selected, issues

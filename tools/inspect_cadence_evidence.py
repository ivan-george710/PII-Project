"""Independent post-run diagnostic checks; emits sanitized metadata only.

Does not rerun OCR or detection, or alter any production dispositions.
Actual values/snippets are written only under the existing restricted cache.
"""
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def shape(value):
    return "".join("X" if c.isupper() else "x" if c.isalpha() else "0" if c.isdigit()
                   else c for c in value)


def main():
    caches = [p.parent for p in (ROOT / ".private_validation").glob("*/metrics.json")
              if (p.parent / "redaction_internal.json").exists()]
    if len(caches) != 1:
        raise RuntimeError("Expected one completed validation cache")
    cache = caches[0]
    extraction = read(cache / "extraction.json")
    detection = read(cache / "detections.json")
    redaction = read(cache / "redaction_internal.json")
    original = {p["page_number"]: p["text"] for p in extraction["pages"]}
    redacted = {p["page_number"]: p["text"] for p in redaction["pages"]}
    applied = redaction["redactions"]
    all_d = detection["detections"] + detection["rejected"] + detection["review"]

    def inspect_span(page, start, end, value, kind):
        intersecting = sorted([r for r in applied if r["page_number"] == page and
                               r["original_start"] < end and start < r["original_end"]],
                              key=lambda r: r["original_start"])
        cursor, remaining = start, []
        for record in intersecting:
            if cursor < record["original_start"]:
                remaining.append(original[page][cursor:min(end, record["original_start"])] )
            cursor = max(cursor, record["original_end"])
        if cursor < end:
            remaining.append(original[page][cursor:end])
        relevant = [d for d in all_d if d["page_number"] == page and d["start"] < end and start < d["end"]]
        return {"kind": kind, "page": page, "start": start, "end": end, "value": value,
                "fully_covered": not remaining, "remaining_parts": remaining,
                "intersecting_dispositions": dict(Counter(d["final_decision"] for d in relevant)),
                "intersecting_entities": dict(Counter(d["entity_type"] for d in relevant))}

    # Only name fields with explicit policy-owner/author labels are used as local
    # likely-positive anchors. Stop before the role title, ID or other field.
    labels = re.compile(r"(?im)\b(policy\s*owner|policyowner|author)\s*:\s*([^\n]{1,160})")
    name_fields = []
    for page, text in original.items():
        for match in labels.finditer(text):
            part = re.split(r"[,;(]", match.group(2), maxsplit=1)[0].strip()
            if not part or not any(c.isalpha() for c in part):
                continue
            start = match.start(2) + len(match.group(2)) - len(match.group(2).lstrip())
            item = inspect_span(page, start, start + len(part), part, "LABELED_PERSON_FIELD")
            item["label"] = match.group(1).lower()
            name_fields.append(item)

    # Diagnostic-only normalized matching maps to exact ORIGINAL regex spans;
    # it never feeds normalized offsets/extra candidates to Engines 3 or 4.
    name_variants = []
    seen = set()
    for anchor in name_fields:
        letters = [c for c in anchor["value"] if c.isalpha()]
        if len(letters) < 6 or len(letters) > 60:
            continue
        pattern = re.compile(r"(?<![A-Za-z])" + r"[\s.]*".join(re.escape(c) for c in letters)
                             + r"(?![A-Za-z])", re.I)
        for page, text in original.items():
            for match in pattern.finditer(text):
                key = (page, match.start(), match.end())
                if key not in seen:
                    seen.add(key)
                    name_variants.append(inspect_span(page, match.start(), match.end(), match.group(),
                                                       "KNOWN_FIELD_NAME_VARIANT"))

    identifier_probes = []
    probes = {
        "EMAIL": re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "EMPLOYEE_ID": re.compile(r"\bEMP-\d{5}\b"),
        "EMPLOYEE_ID_OCR_VARIANT": re.compile(r"\bEMP\s*[-–—]\s*\d(?:\s*\d){4}\b", re.I),
        "PHONE_SHAPED": re.compile(r"(?<!\w)(?:\+\d{1,3}[\s.-]*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]+\d{4}(?!\d)"),
    }
    for kind, pattern in probes.items():
        for page, text in original.items():
            for match in pattern.finditer(text):
                identifier_probes.append(inspect_span(page, match.start(), match.end(), match.group(), kind))

    context_terms = ["policyowner", "author", "risk", "group", "framework", "approval", "version",
                     "page", "bank", "account", "ssn", "passport", "license", "iban", "phone", "email"]
    government = {"US_SSN", "US_PASSPORT", "US_DRIVER_LICENSE", "US_ITIN", "US_BANK_NUMBER",
                  "IBAN_CODE", "CREDIT_CARD", "MEDICAL_LICENSE"}
    representatives = []
    private_representatives = []
    for entity in ["PERSON", "EMPLOYEE_ID", "EMAIL_ADDRESS", "PHONE_NUMBER"] + sorted(government):
        for disposition in ["CONFIRM", "REJECT", "REVIEW"]:
            records = [d for d in all_d if d["entity_type"] == entity and d["final_decision"] == disposition]
            # Include a broad sample of PERSON decisions without printing an inventory.
            selected = records[:4]
            if entity == "PERSON":
                selected += [d for d in records if re.search(r"[a-z][A-Z]|[:\n]", d["text"])][:2]
            for d in selected:
                context = original[d["page_number"]][max(0, d["start"] - 65):d["end"] + 65]
                private_representatives.append({"detection": d, "context": context})
                representatives.append({"entity": entity, "disposition": disposition,
                    "page": d["page_number"], "start": d["start"], "end": d["end"],
                    "shape": shape(d["text"]), "characters": len(d["text"]),
                    "confidence": d["confidence"], "recognizer": d["recognizer"],
                    "validation_reason": d["validation_reason"], "llm_decision": d["llm_decision"],
                    "source_block": d["source_block"],
                    "context_cues": [term for term in context_terms if term in context.lower()]})

    # Closed-vocabulary ordinary role/business phrases can be assessed locally.
    # Expose only the dictionary matches, never arbitrary text containing a name.
    from sys import path
    path.insert(0, str(ROOT))
    from app.engines.pii_detection.validation import BUSINESS_WORDS, _business_label
    possible_false_positives = []
    for d in detection["detections"]:
        if d["entity_type"] != "PERSON":
            continue
        value = d["text"]
        cue_hits = sorted({term for term in BUSINESS_WORDS if term in value.lower() and len(term) >= 4})
        if cue_hits:
            possible_false_positives.append({"page": d["page_number"], "start": d["start"],
                "end": d["end"], "shape": shape(value), "business_cues": cue_hits,
                "closed_business_label": _business_label(value), "llm_decision": d["llm_decision"]})

    identifier_context_flags = []
    supporting_context = {
        "US_BANK_NUMBER": r"bank\s*account|account\s*(?:number|no)|banking|iban",
        "US_DRIVER_LICENSE": r"driver.?s?\s*licen[sc]e|driving\s*licen[sc]e|\bdl\s*number|licen[sc]e\s*number",
        "US_PASSPORT": r"passport", "US_SSN": r"\bssn\b|social\s*security",
        "US_ITIN": r"\bitin\b|taxpayer", "CREDIT_CARD": r"credit\s*card|card\s*number",
    }
    for d in detection["detections"]:
        if d["entity_type"] not in supporting_context:
            continue
        context = original[d["page_number"]][max(0, d["start"] - 200):d["end"] + 200]
        if not re.search(supporting_context[d["entity_type"]], context, re.I):
            identifier_context_flags.append({"entity": d["entity_type"], "page": d["page_number"],
                "start": d["start"], "end": d["end"], "shape": shape(d["text"]),
                "confidence": d["confidence"], "llm_decision": d["llm_decision"],
                "reason": "confirmed_identifier_without_entity_specific_context"})

    private = {"name_fields": name_fields, "name_variants": name_variants,
               "identifier_probes": identifier_probes, "representatives_with_context": private_representatives}
    (cache / "independent_sensitive_inspection.json").write_text(
        json.dumps(private, ensure_ascii=False, indent=2), encoding="utf-8")

    def sanitized(items):
        return [{k: v for k, v in item.items() if k not in {"value", "remaining_parts"}} |
                {"shape": shape(item["value"]), "remaining_shapes": [shape(p) for p in item["remaining_parts"]]}
                for item in items]

    summary = {
        "labeled_name_fields": sanitized(name_fields),
        "known_name_variant_count": len(name_variants),
        "uncovered_known_name_variant_count": sum(not v["fully_covered"] for v in name_variants),
        "uncovered_known_name_variants": sanitized([v for v in name_variants if not v["fully_covered"]]),
        "identifier_checks": {kind: {"original_matches": sum(p["kind"] == kind for p in identifier_probes),
            "uncovered_matches": sum(p["kind"] == kind and not p["fully_covered"] for p in identifier_probes),
            "redacted_matches": sum(len(list(pattern.finditer(text))) for text in redacted.values())}
            for kind, pattern in probes.items()},
        "uncovered_identifier_examples": sanitized([p for p in identifier_probes if not p["fully_covered"]])[:12],
        "representatives": representatives,
        "possible_confirmed_person_false_positives": possible_false_positives,
        "confirmed_identifiers_without_supporting_context": identifier_context_flags,
        "government_banking_candidate_counts": dict(Counter(d["entity_type"] for d in all_d
                                                            if d["entity_type"] in government)),
    }
    (cache / "independent_sanitized_inspection.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"labeled_name_fields": len(name_fields),
        "uncovered_name_fields": sum(not f["fully_covered"] for f in name_fields),
        "known_name_variant_count": summary["known_name_variant_count"],
        "uncovered_known_name_variant_count": summary["uncovered_known_name_variant_count"],
        "identifier_checks": summary["identifier_checks"],
        "possible_person_false_positive_flags": len(possible_false_positives),
        "identifier_without_supporting_context_flags": len(identifier_context_flags)}))


if __name__ == "__main__":
    main()

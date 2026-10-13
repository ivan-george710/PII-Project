"""Private Office review artifacts, always regenerated from a fingerprinted source."""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4
from zipfile import ZipFile

from lxml import etree
from app.engines.audit.storage import AuditStore, PROJECT_ROOT
from app.engines.extraction.office import NS, node_text, parse_xml, source_hash
from app.engines.extraction.docx import extract_docx
from app.engines.extraction.pptx import extract_pptx
from .engine import RedactionEngine


class ArtifactValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactMappingIssue:
    page_number: int
    original_start: int
    original_end: int
    entity_type: str
    code: str = "cross_structure_span"


@dataclass
class ArtifactResult:
    path: Path | None = None  # Sensitive internal location, never in public summary.
    redaction_completed: bool = False
    verification_completed: bool = False
    reopened: bool = False
    supported_content_verified: bool = False
    mapping_failures: int = 0
    verification_failures: int = 0
    residual_confirmed_values: int = 0
    residual_sensitive_patterns: int = 0
    unsupported_structures: dict[str, int] = field(default_factory=dict)
    applied_redactions: int = 0
    known_review_complete: bool = False
    mapping_issues: list[ArtifactMappingIssue] = field(default_factory=list)
    format: str | None = None
    source_sha256: str | None = None
    page_count_preserved: bool = False
    region_checks: list[dict] = field(default_factory=list)  # Internal visual mapping evidence.
    visual_inspection_completed: bool = False
    face_transformations_verified: bool = False
    protected_faces: int = 0
    face_mapping_failures: int = 0
    face_verification_failures: int = 0
    unsupported_visual_content: dict[str,int] = field(default_factory=dict)
    visual_checks: list[dict] = field(default_factory=list)
    protected_face_ids: list[str] = field(default_factory=list)

    @property
    def output_path(self):
        return self.path

    @property
    def mapping_issue_count(self):
        return self.mapping_failures

    @property
    def verification_failure_count(self):
        return self.verification_failures

    @property
    def artifact_verified(self):
        return (self.verification_completed and self.supported_content_verified
                and not self.mapping_failures and not self.verification_failures
                and not self.unsupported_structures and not self.residual_confirmed_values
                and not self.residual_sensitive_patterns and self.known_review_complete
                and (not self.visual_inspection_completed or self.face_transformations_verified))

    @property
    def safe_for_llm(self):
        return False

    @property
    def coverage_verified(self):
        return False

    @property
    def downstream_export_permitted(self):
        return False

    def sanitized_summary(self):
        # Only fixed issue categories produced by extractors and aggregate numeric/boolean fields.
        categories = {"media_without_ocr", "embedded_objects", "unmapped_text_nodes", "text_boxes",
                      "embedded_documents", "content_controls", "tracked_changes", "dynamic_fields",
                      "alternative_text", "external_relationships", "document_properties",
                      "annotations_or_notes_parts", "charts_or_diagrams", "pdf_annotations_or_attachments", "pdf_images_without_ocr"}
        from app.engines.visual_detection.models import VISUAL_ISSUES
        return {"format": self.format if self.format in {"pdf", "docx", "pptx", "image"} else None,
                "page_count_preserved": self.page_count_preserved,
                "redaction_completed": self.redaction_completed,
                "verification_completed": self.verification_completed, "reopened": self.reopened,
                "supported_content_verified": self.supported_content_verified,
                "artifact_verified": self.artifact_verified, "mapping_failures": self.mapping_failures,
                "verification_failures": self.verification_failures,
                "residual_confirmed_values": self.residual_confirmed_values,
                "residual_sensitive_patterns": self.residual_sensitive_patterns,
                "unsupported_structures": {k: v for k, v in self.unsupported_structures.items() if k in categories},
                "applied_redactions": self.applied_redactions,
                "visual_inspection_completed":self.visual_inspection_completed,
                "face_transformations_verified":self.face_transformations_verified,
                "protected_faces":self.protected_faces,"face_mapping_failures":self.face_mapping_failures,
                "face_verification_failures":self.face_verification_failures,
                "unsupported_visual_content":{k:v for k,v in self.unsupported_visual_content.items() if k in VISUAL_ISSUES},
                "safe_for_llm": False, "coverage_verified": False, "downstream_export_permitted": False}


def _find(root, path):
    nodes = root.xpath(path, namespaces=NS)
    if len(nodes) != 1:
        raise ArtifactValidationError("Source mapping is not unique")
    return nodes[0]


def _set_text(node, text):
    if etree.QName(node).localname != "t":
        node.tag = "{" + etree.QName(node).namespace + "}t"
        node.attrib.clear()
    node.text = text
    if etree.QName(node).namespace == NS["w"]:
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def _replace(nodes, start, end, tag):
    selected = [(mapping, node) for mapping, node in nodes if mapping.start < end and start < mapping.end]
    if not selected:
        raise ArtifactValidationError("Replacement lacks mapped text")
    for index, (mapping, node) in enumerate(selected):
        value = node_text(node)
        left, right = max(0, start - mapping.start), min(mapping.end, end) - mapping.start
        _set_text(node, value[:left] + (tag if index == 0 else "") + value[right:])


def _structure_signature(data):
    root = parse_xml(data)
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        q = etree.QName(node)
        if q.namespace in {NS["w"], NS["a"]} and q.localname in {"t", "tab", "br", "cr"}:
            node.tag = "{" + q.namespace + "}t"
            node.text = ""
            node.attrib.pop("{http://www.w3.org/XML/1998/namespace}space", None)
    return etree.tostring(root, method="c14n")


def _span_segments(extraction, record):
    """Map only actual confirmed characters; structural newlines remain structural."""
    segments = extraction.structure.segments
    matches = [(i, s) for i, s in enumerate(segments) if s.page_number == record.page_number
               and s.start < record.original_end and record.original_start < s.end]
    if not matches:
        return []
    page = next(p for p in extraction.pages if p.page_number == record.page_number)
    if extraction.file_type == "docx":
        return matches if len(matches) == 1 and matches[0][1].start <= record.original_start and record.original_end <= matches[0][1].end else []
    # Gaps must be precisely the extractor's one-character paragraph separator.
    cursor = record.original_start
    for _, segment in matches:
        gap = page.text[cursor:min(segment.start, record.original_end)] if cursor < segment.start else ""
        if gap not in {"", "\n"}:
            return []
        cursor = min(record.original_end, segment.end)
    if page.text[cursor:record.original_end] not in {"", "\n"}:
        return []
    if len(matches) > 1:
        first = matches[0][1]
        keys = ("kind", "shape_id", "group_ids", "row", "column")
        for (_, before), (_, after) in zip(matches, matches[1:]):
            if (before.part != after.part or any(before.location.get(k) != after.location.get(k) for k in keys)
                    or after.location.get("paragraph") != before.location.get("paragraph", -2) + 1
                    or page.text[before.end:after.start] != "\n"):
                return []
    return matches


def _segment_edits(extraction, redaction):
    edits, issues = defaultdict(list), []
    for record in redaction.redactions:
        if next(p for p in extraction.pages if p.page_number == record.page_number).extraction_method == "media_ocr":
            continue
        matches = _span_segments(extraction, record)
        if not matches:
            issues.append(ArtifactMappingIssue(record.page_number, record.original_start,
                                               record.original_end, record.entity_type))
            continue
        for position, (index, segment) in enumerate(matches):
            start, end = max(record.original_start, segment.start) - segment.start, min(record.original_end, segment.end) - segment.start
            edits[index].append((start, end, record.tag if position == 0 else ""))
    return edits, issues


class OfficeArtifactEngine:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir is not None else PROJECT_ROOT / ".private_artifacts"

    def redact(self, extraction, effective_detection, redaction) -> ArtifactResult:
        if extraction.file_type not in {"docx", "pptx"} or extraction.structure is None:
            raise ArtifactValidationError("Office structural mappings are required")
        if RedactionEngine().redact(extraction, effective_detection) != redaction:
            raise ArtifactValidationError("Artifact decisions differ from current text redaction")
        source = Path(extraction.source_path)
        if source_hash(source) != extraction.structure.source_sha256:
            raise ArtifactValidationError("Original source integrity check failed")
        result = ArtifactResult(unsupported_structures=deepcopy(extraction.structure.limitations),
                                known_review_complete=redaction.redaction_complete, format=extraction.file_type,
                                source_sha256=extraction.structure.source_sha256)
        with ZipFile(source) as archive:
            members = {info.filename: archive.read(info) for info in archive.infolist()}
            infos = archive.infolist()
        if len(members) != len(infos):
            raise ArtifactValidationError("Ambiguous duplicate package members")
        from .visual_artifacts import prepare_visual
        visual_plans=prepare_visual(extraction,result)
        visual_members={unit.source_ref:data for unit,data,_ in visual_plans.values()}
        from .media_artifacts import media_plans, update_face_checks
        media = media_plans(extraction, redaction, visual_members)
        update_face_checks(visual_plans, media)
        visual_members.update({part: data for part,(data,_) in media.items()})
        roots = {part: parse_xml(members[part]) for part in {s.part for s in extraction.structure.segments}}
        pages = {p.page_number: p for p in extraction.pages}
        segment_nodes = {}
        seen = set()
        for index, segment in enumerate(extraction.structure.segments):
            if (segment.part, segment.paragraph_path) in seen:
                raise ArtifactValidationError("Duplicate paragraph mapping")
            seen.add((segment.part, segment.paragraph_path))
            paragraph = _find(roots[segment.part], segment.paragraph_path)
            nodes = [(n, _find(roots[segment.part], n.path)) for n in segment.nodes]
            cursor = 0
            for mapping, node in nodes:
                if (paragraph not in node.iterancestors() or mapping.start != cursor
                        or mapping.end != cursor + len(node_text(node))):
                    raise ArtifactValidationError("Source text node mapping differs")
                cursor = mapping.end
            text = "".join(node_text(node) for _, node in nodes)
            page = pages[segment.page_number]
            if not 0 <= segment.start <= segment.end <= len(page.text) or page.text[segment.start:segment.end] != text:
                raise ArtifactValidationError("Mapped source paragraph differs")
            segment_nodes[index] = nodes
        edits, result.mapping_issues = _segment_edits(extraction, redaction)
        result.mapping_failures = len(result.mapping_issues)
        # Unmappable spans remain untouched in a private review copy. They block
        # verification/clearance and are linked to source offsets for the reviewer.
        changed = set()
        for index, records in edits.items():
            segment = extraction.structure.segments[index]
            for start, end, tag in sorted(records, reverse=True):
                _replace(segment_nodes[index], start, end, tag)
            changed.add(segment.part)
        store = AuditStore(self.output_dir)
        store._prepare()  # Reuse the existing private-directory ACL and path guards; no audit store is added.
        self.output_dir = store.directory
        output = self.output_dir / ("review_" + uuid4().hex + "." + extraction.file_type)
        if output.resolve() == source.resolve():
            raise ArtifactValidationError("Output may not overwrite the original")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.output_dir, prefix=".artifact-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                if os.name != "nt":
                    os.fchmod(stream.fileno(), 0o600)
            with ZipFile(temporary, "w") as archive:
                for info in infos:
                    data = (etree.tostring(roots[info.filename], xml_declaration=True, encoding="UTF-8", standalone=True)
                            if info.filename in changed else visual_members.get(info.filename,members[info.filename]))
                    archive.writestr(info, data)
            os.replace(temporary, output)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        result.path = output
        result.redaction_completed = True
        result.applied_redactions = len(redaction.redactions) - result.mapping_failures
        return result

    def verify(self, extraction, redaction, result: ArtifactResult) -> ArtifactResult:
        checked = deepcopy(result)
        checked.verification_completed = True
        checked.verification_failures = 0
        checked.reopened = False
        checked.supported_content_verified = False
        checked.residual_confirmed_values = 0
        checked.residual_sensitive_patterns = 0
        if not checked.redaction_completed or checked.path is None:
            checked.verification_failures += 1
            return checked
        try:
            if source_hash(extraction.source_path) != extraction.structure.source_sha256:
                raise ArtifactValidationError("Source integrity changed before verification")
            output = (extract_docx if extraction.file_type == "docx" else extract_pptx)(checked.path)
            checked.reopened = True
            with ZipFile(extraction.source_path) as source, ZipFile(checked.path) as generated:
                if source.namelist() != generated.namelist():
                    checked.verification_failures += 1
                else:
                    mapped_parts = {s.part for s in extraction.structure.segments}
                    visual_parts={c['source_ref'] for c in checked.visual_checks if c['kind']=='office_media'}
                    visual_parts.update(p.media_source['part'] for p in extraction.pages if p.media_source)
                    for part in source.namelist():
                        original, modified = source.read(part), generated.read(part)
                        if original == modified:
                            continue
                        if part in visual_parts:continue  # Independently checked below; XML placement remains byte-identical.
                        if part not in mapped_parts or _structure_signature(original) != _structure_signature(modified):
                            checked.verification_failures += 1
            # Independent extraction re-enumerates all supported structures, including headers/notes.
            edits, issues = _segment_edits(extraction, redaction)
            checked.verification_failures += len(issues)
            original_pages = {p.page_number: p.text for p in extraction.pages}
            native_pages = [p for p in extraction.pages if p.extraction_method != "media_ocr"]
            if len(native_pages) != len(output.pages):
                checked.verification_failures += 1
            checked.page_count_preserved = len(native_pages) == len(output.pages)
            for index, (segment, generated) in enumerate(zip(extraction.structure.segments, output.structure.segments)):
                expected = original_pages[segment.page_number][segment.start:segment.end]
                for start, end, tag in sorted(edits[index], reverse=True):
                    expected = expected[:start] + tag + expected[end:]
                page = next(p for p in output.pages if p.page_number == generated.page_number)
                if page.text[generated.start:generated.end] != expected:
                    checked.verification_failures += 1
            original_locations = [(s.page_number, s.part, s.paragraph_path, s.location) for s in extraction.structure.segments]
            output_locations = [(s.page_number, s.part, s.paragraph_path, s.location) for s in output.structure.segments]
            if original_locations != output_locations:
                checked.verification_failures += 1
            values = {r.original_text for r in redaction.redactions}
            checked.residual_confirmed_values = sum(output.full_text.count(v) for v in values)
            checked.residual_sensitive_patterns = len(re.findall(
                r"\bEMP-\d{5}\b|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|\b\d{3}-\d{2}-\d{4}\b", output.full_text))
            from .media_artifacts import verify_media
            verify_media(extraction, redaction, checked)
            checked.supported_content_verified = checked.verification_failures == 0
            checked.unsupported_structures = output.structure.limitations
            if any(p.media_source for p in extraction.pages):
                checked.unsupported_structures.pop("media_without_ocr", None)
        except Exception:
            checked.verification_failures += 1
            checked.supported_content_verified = False
        from .visual_artifacts import verify_visual
        return verify_visual(extraction,checked,redaction)

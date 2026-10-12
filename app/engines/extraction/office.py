"""Exact OOXML paragraph mapping shared by the two Office extractors."""
from collections import Counter
import hashlib
from pathlib import Path
from zipfile import ZipFile

from lxml import etree
from .models import SourceTextNode, SourceSegment

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS = {"w": W, "a": A, "p": P}


def parse_xml(data):
    return etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True))


def node_text(node):
    name = etree.QName(node).localname
    if name in {"t", "delText", "instrText"}:
        return node.text or ""
    if name == "tab":
        return "\t"
    if name in {"br", "cr"}:
        return "\n"
    return ""


def paragraph_segment(paragraph, part, page_number, start, location):
    namespace = etree.QName(paragraph).namespace
    values, nodes = [], []
    cursor = 0
    for node in paragraph.iter():
        if not isinstance(node.tag, str):
            continue
        q = etree.QName(node)
        if q.namespace != namespace or q.localname not in {"t", "tab", "br", "cr"}:
            continue
        # Text boxes and other nested paragraphs are separate, unsupported content.
        if next((p for p in node.iterancestors() if p.tag == paragraph.tag), None) is not paragraph:
            continue
        value = node_text(node)
        nodes.append(SourceTextNode(node.getroottree().getpath(node), cursor, cursor + len(value),
                                    "text" if q.localname == "t" else q.localname))
        values.append(value)
        cursor += len(value)
    text = "".join(values)
    return text, SourceSegment(page_number, part, paragraph.getroottree().getpath(paragraph),
                               start, start + len(text), nodes, location)


def package_limitations(path, mapped_parts, mapped_text_nodes):
    """Conservative inventory of content not covered by editable paragraph mappings."""
    counts = Counter()
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith(("word/media/", "ppt/media/")):
                counts["media_without_ocr"] += 1
            if "/embeddings/" in name or "/activeX/" in name:
                counts["embedded_objects"] += 1
            if not name.endswith((".xml", ".rels")):
                continue
            root = parse_xml(archive.read(name))
            tree = root.getroottree()
            for node in root.iter():
                if not isinstance(node.tag, str):
                    continue
                q = etree.QName(node)
                if q.namespace in {W, A} and q.localname == "t" and node.text:
                    if (name, tree.getpath(node)) not in mapped_text_nodes:
                        counts["unmapped_text_nodes"] += 1
                if q.namespace == W and q.localname in {"txbxContent", "altChunk", "sdt", "ins", "del"}:
                    counts[{"txbxContent": "text_boxes", "altChunk": "embedded_documents",
                            "sdt": "content_controls", "ins": "tracked_changes", "del": "tracked_changes"}[q.localname]] += 1
                if q.namespace == W and q.localname in {"instrText", "fldSimple"}:
                    counts["dynamic_fields"] += 1
                if q.namespace == A and q.localname == "fld":
                    counts["dynamic_fields"] += 1
                if q.localname in {"docPr", "cNvPr"} and any(node.get(a) for a in ("descr", "title")):
                    counts["alternative_text"] += 1
                if q.localname == "Relationship" and node.get("TargetMode") == "External":
                    counts["external_relationships"] += 1
            if name.startswith("docProps/") and any(n.text and n.text.strip() for n in root.iter()):
                counts["document_properties"] += 1
            if "comments" in name.lower() or "footnotes" in name or "endnotes" in name:
                counts["annotations_or_notes_parts"] += 1
            if "/charts/" in name or "/diagrams/" in name:
                counts["charts_or_diagrams"] += 1
    return dict(sorted(counts.items()))


def source_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

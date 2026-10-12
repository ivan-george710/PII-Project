"""DOCX body/table/header/footer paragraphs as logical segments, never physical pages."""
from pathlib import Path
from docx import Document

from .models import ExtractionResult, ExtractedPage, StructureMap
from .office import W, paragraph_segment, package_limitations, source_hash


def extract_docx(file_path) -> ExtractionResult:
    path = Path(file_path)
    document = Document(path)
    # Package parts avoid duplication of headers/footers shared by linked sections.
    parts = [document.part]
    parts.extend(sorted((p for p in document.part.package.parts
                         if str(p.partname).startswith(("/word/header", "/word/footer"))
                         and str(p.partname).endswith(".xml")), key=lambda p: str(p.partname)))
    pages, segments = [], []
    for part in parts:
        name = str(part.partname).lstrip("/")
        root = part.element
        for paragraph in root.iter(f"{{{W}}}p"):
            if any(a.tag in {f"{{{W}}}{tag}" for tag in ("txbxContent", "sdt", "ins", "del")}
                   for a in paragraph.iterancestors()):
                continue
            number = len(pages) + 1
            ancestors = list(paragraph.iterancestors())
            location = {"kind": "header" if "/header" in name else "footer" if "/footer" in name else "body",
                        "table_depth": sum(a.tag == f"{{{W}}}tbl" for a in ancestors),
                        "logical_segment": number}
            text, segment = paragraph_segment(paragraph, name, number, 0, location)
            pages.append(ExtractedPage(number, text, "docx"))
            segments.append(segment)
    mapped = {(s.part, n.path) for s in segments for n in s.nodes if n.kind == "text"}
    structure = StructureMap(source_hash(path), "docx_logical_paragraph", segments,
                             package_limitations(path, {s.part for s in segments}, mapped))
    return ExtractionResult(path, path.name, "docx", pages, structure)

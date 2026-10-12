"""Slide-local text including recursive groups, tables and accessible speaker notes."""
from pathlib import Path
from zipfile import ZipFile
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

from .models import ExtractionResult, ExtractedPage, StructureMap
from .office import paragraph_segment, package_limitations, source_hash, parse_xml, NS


def _paragraphs(shapes, group_ids=(), notes=False):
    for shape in shapes:
        location = {"kind": "notes" if notes else "shape", "shape_id": shape.shape_id,
                    "group_ids": list(group_ids)}
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _paragraphs(shape.shapes, (*group_ids, shape.shape_id), notes)
        elif shape.has_table:
            for row, cells in enumerate(shape.table.rows):
                for col, cell in enumerate(cells.cells):
                    # Spanned cells contain no separate visible text; do not duplicate merge origins.
                    for index, paragraph in enumerate(cell.text_frame.paragraphs):
                        yield paragraph._p, location | {"kind": "table", "row": row, "column": col,
                                                       "paragraph": index}
        elif shape.has_text_frame:
            if notes and (not shape.is_placeholder or shape.placeholder_format.type != PP_PLACEHOLDER.BODY):
                continue
            for index, paragraph in enumerate(shape.text_frame.paragraphs):
                yield paragraph._p, location | {"paragraph": index}


def extract_pptx(file_path) -> ExtractionResult:
    path = Path(file_path)
    presentation = Presentation(path)
    with ZipFile(path) as archive:
        raw_parts = {name: archive.read(name) for name in archive.namelist()
                     if name.startswith(("ppt/slides/slide", "ppt/notesSlides/notesSlide")) and name.endswith(".xml")}
    roots = {name: parse_xml(data) for name, data in raw_parts.items()}
    pages, segments = [], []
    for number, slide in enumerate(presentation.slides, 1):
        entries = [(p, str(slide.part.partname).lstrip("/"), loc) for p, loc in _paragraphs(slide.shapes)]
        if slide.has_notes_slide:
            notes = slide.notes_slide
            entries.extend((p, str(notes.part.partname).lstrip("/"), loc)
                           for p, loc in _paragraphs(notes.shapes, notes=True))
        values, cursor = [], 0
        for paragraph, name, loc in entries:
            # python-pptx adds an empty paragraph when accessing a placeholder
            # whose source txBody has none. Do not invent a source mapping for it.
            matches = roots[name].xpath(paragraph.getroottree().getpath(paragraph), namespaces=NS)
            if not matches:
                text, _ = paragraph_segment(paragraph, name, number, 0, loc)
                if not text:
                    continue
                raise ValueError("Slide paragraph is absent from the source package")
            if len(matches) != 1:
                raise ValueError("Slide paragraph source mapping is ambiguous")
            paragraph = matches[0]
            if values:
                cursor += 1  # Explicit newline separator has no editable source node.
            text, segment = paragraph_segment(paragraph, name, number, cursor, loc | {"slide": number})
            values.append(text)
            segments.append(segment)
            cursor += len(text)
        pages.append(ExtractedPage(number, "\n".join(values), "pptx"))
    mapped = {(s.part, n.path) for s in segments for n in s.nodes if n.kind == "text"}
    structure = StructureMap(source_hash(path), "pptx_slide", segments,
                             package_limitations(path, {s.part for s in segments}, mapped))
    return ExtractionResult(path, path.name, "pptx", pages, structure)

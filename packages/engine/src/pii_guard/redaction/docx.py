from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from uuid import UUID

from docx import Document

from pii_guard.models import ExtractedTextBlock, SanitizedArtifact
from pii_guard.rules.policy import RedactionTarget
from pii_guard.redaction.metadata import sanitize_office_metadata
from pii_guard.redaction.office import (
    W, A, R, failure, inspect_editable, inspect_package, pack, paragraph_units,
    publish, relationships, rewrite_media, rewrite_unit, serialize, unpack, validate_inputs, xml,
)


def redact_docx(data: bytes, targets: Iterable[RedactionTarget] = (), *, artifact_id: UUID,
                blocks: Iterable[ExtractedTextBlock] = (), region_sources=(), submission_id: UUID | None = None) -> bytes:
    """Rewrite supported Word paragraphs, tables and inline PNG/JPEG pictures.

    Original extraction blocks bind private targets to exact part-local text.
    Non-stock ancillary parts, fields, revisions, hidden text and floating drawings
    fail closed. Public findings are neither consumed nor modified.
    """
    try:
        parts = unpack(data)
        sanitize_office_metadata(parts, 'docx')
        editable = {'word/document.xml'}
        rels = relationships(parts)
        inspect_package(parts, 'docx', editable, rels)
        if rels.get('', {}).get('rId1') != ('word/document.xml', R + '/officeDocument'):
            raise ValueError('Unsupported main document relationship')
        root = xml(parts['word/document.xml'])
        if root.tag != f'{{{W}}}document':
            raise ValueError('Invalid Word document')
        inspect_editable(root, 'docx')
        native = {}
        for index, (p, nodes, text) in enumerate(paragraph_units(root, W)):
            native[f'docx:part:/word/document.xml:paragraph:{index}'] = (p, nodes, text, None)
        # Match extraction's complete ancillary paragraph inventory for integrity;
        # those parts may be reported, but cannot be rewritten in this phase.
        for name, content in parts.items():
            if name.startswith('word/') and name.endswith('.xml') and name not in editable:
                for index, (p, nodes, text) in enumerate(paragraph_units(xml(content), W)):
                    native[f'docx:part:/{name}:paragraph:{index}'] = (p, nodes, text, None)
        images = {}
        used = set()
        for blip in root.iter(f'{{{A}}}blip'):
            rid = blip.get(f'{{{R}}}embed')
            media, reltype = rels['word/document.xml'][rid]
            if reltype != R + '/image' or '/media/' not in media:
                raise ValueError('Invalid picture relationship')
            used.add(rid)
            images[f'docx:part:/word/document.xml:image:{rid}'] = (media, None, None)
        if used != {rid for rid, (_, typ) in rels['word/document.xml'].items() if typ == R + '/image'}:
            raise ValueError('Unplaced Word image')
        known, grouped = validate_inputs(artifact_id, blocks, targets, native, images, region_sources)
        for ref, unit_targets in grouped.items():
            if known[ref].location.kind != 'native_text':
                continue
            if not ref.startswith('docx:part:/word/document.xml:'):
                raise ValueError('Unsupported ancillary text target')
            p, nodes, text, _ = native[ref]
            expected = rewrite_unit(nodes, text, unit_targets, known[ref].location, W)
            actual = paragraph_units(p, W)
            if len(actual) != 1 or actual[0][2] != expected:
                raise ValueError('Word run rewrite did not complete')
        rewrite_media(parts, images, known, grouped, artifact_id)
        parts['word/document.xml'] = serialize(root)
        output = pack(parts)
        Document(BytesIO(output))  # Package integrity before returning bytes.
        return output
    except Exception:
        raise failure('docx', artifact_id, submission_id) from None


def redact_docx_file(source_path: Path, output_path: Path, targets: Iterable[RedactionTarget] = (), *,
                     artifact_id: UUID, blocks: Iterable[ExtractedTextBlock] = (),
                     submission_id: UUID | None = None) -> SanitizedArtifact:
    """Publish a fresh DOCX exclusively after the entire rewrite succeeds."""
    return publish(redact_docx, 'docx', source_path, output_path, targets,
        artifact_id=artifact_id, blocks=blocks, submission_id=submission_id)

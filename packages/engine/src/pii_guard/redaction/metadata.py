"""Private ancillary-content policy shared by the existing format writers.

Classification describes the treatment of a structure, never its original value.
Unknown structures fail closed; no metadata strings are returned or logged.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal
import re
import struct
import zlib

from lxml import etree as ET
from pypdf.generic import (
    BooleanObject, ByteStringObject, DictionaryObject, FloatObject, NameObject,
    NullObject, NumberObject, StreamObject, TextStringObject,
)

from pii_guard.models import EngineBaseModel


class AncillaryClass(str, Enum):
    SANITIZED = 'supported_sanitized'
    STRUCTURAL = 'safe_structural'
    STRIPPED = 'stripped'
    UNSUPPORTED = 'unsupported'


class AncillaryDecision(EngineBaseModel):
    structure: Literal['office_properties', 'office_preview', 'office_printer_data',
        'office_shape_metadata', 'office_structural', 'office_editable', 'office_media',
        'office_unknown', 'pdf_info', 'pdf_xmp', 'image_metadata']
    disposition: AncillaryClass


class AncillaryReport(EngineBaseModel):
    decisions: tuple[AncillaryDecision, ...] = ()

    @property
    def warnings(self) -> tuple[str, ...]:
        # Fixed messages only: no part names, metadata values or external URLs.
        messages = {
            'office_properties': 'Office document properties were removed.',
            'office_preview': 'Office preview images were removed.',
            'office_printer_data': 'Office printer settings were removed.',
            'office_shape_metadata': 'Office shape descriptions were removed.',
            'pdf_info': 'PDF document properties were removed.',
            'pdf_xmp': 'PDF XML metadata was removed.',
            'image_metadata': 'Image metadata was removed.',
        }
        return tuple(sorted({messages[d.structure] for d in self.decisions
            if d.structure in messages and d.disposition in {AncillaryClass.STRIPPED, AncillaryClass.SANITIZED}}))


def classify_office_part(name, data, stock, editable, kind) -> AncillaryDecision:
    """Classification is followed by the writer's relationship/XML validation."""
    if name in editable or kind == 'pptx' and name == 'ppt/presentation.xml':
        return AncillaryDecision(structure='office_editable', disposition=AncillaryClass.SANITIZED)
    if re.fullmatch(fr'{"word" if kind == "docx" else "ppt"}/media/image[0-9]+\.(png|jpe?g)', name):
        return AncillaryDecision(structure='office_media', disposition=AncillaryClass.SANITIZED)
    if name == '[Content_Types].xml' or name.endswith('.rels') or stock.get(name) == data:
        return AncillaryDecision(structure='office_structural', disposition=AncillaryClass.STRUCTURAL)
    return AncillaryDecision(structure='office_unknown', disposition=AncillaryClass.UNSUPPORTED)


_CORE = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'
_APP = 'http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
_CUSTOM = 'http://schemas.openxmlformats.org/officeDocument/2006/custom-properties'
_VT = 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
_DC = 'http://purl.org/dc/elements/1.1/'
_DATES = 'http://purl.org/dc/terms/'
_XSI = 'http://www.w3.org/2001/XMLSchema-instance'
_PROPERTIES = {
    'docProps/core.xml': (_CORE, 'coreProperties', 'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties'),
    'docProps/app.xml': (_APP, 'Properties', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties'),
    'docProps/custom.xml': (_CUSTOM, 'Properties', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties'),
}


def _validate_properties(data, name):
    from pii_guard.redaction.office import xml
    root = xml(data)
    namespace, local, _ = _PROPERTIES[name]
    if root.tag != f'{{{namespace}}}{local}' or root.attrib or root.text and root.text.strip():
        raise ValueError('Malformed Office properties')
    allowed = {namespace, _VT} if name != 'docProps/core.xml' else {namespace, _DC, _DATES}
    for node in root.iter():
        if ET.QName(node).namespace not in allowed or node.tail and node.tail.strip():
            raise ValueError('Unsupported properties structure')
    if name == 'docProps/core.xml':
        fields = {_CORE: {'keywords', 'lastModifiedBy', 'revision', 'category', 'contentStatus', 'version', 'lastPrinted'},
                  _DC: {'title', 'subject', 'creator', 'description', 'language', 'identifier'},
                  _DATES: {'created', 'modified'}}
        for child in root:
            q = ET.QName(child)
            if q.localname not in fields.get(q.namespace, set()) or len(child) or set(child.attrib) - {f'{{{_XSI}}}type'}:
                raise ValueError('Unsupported core properties')
    if name == 'docProps/custom.xml':
        seen = set()
        for child in root:
            if child.tag != f'{{{_CUSTOM}}}property' or set(child.attrib) != {'fmtid', 'pid', 'name'} or len(child) != 1:
                raise ValueError('Malformed custom property')
            if child.get('fmtid', '').upper() != '{D5CDD505-2E9C-101B-9397-08002B2CF9AE}' or not re.fullmatch(r'[0-9]+', child.get('pid', '')):
                raise ValueError('Invalid custom property identifier')
            if int(child.get('pid')) < 2 or child.get('pid') in seen or ET.QName(child[0]).namespace != _VT:
                raise ValueError('Ambiguous custom property')
            seen.add(child.get('pid'))


def sanitize_office_metadata(parts: dict[str, bytes], kind: Literal['docx', 'pptx']) -> AncillaryReport:
    """Strip only non-rendered, recognized parts and their package references.

    Properties and previews do not affect native block indices or image placement.
    Arbitrary custom XML, comments, notes text and other parts are NOT discarded.
    They must pass the existing writer's complete supported-structure checks.
    """
    from pii_guard.redaction.office import P, R, relationships, serialize, xml
    if kind not in {'docx', 'pptx'}:
        raise ValueError('Unsupported Office format')
    rels = relationships(parts)  # Validate even relationships that will be removed.
    removed, decisions = {}, []
    for name in parts:
        if name in _PROPERTIES:
            _validate_properties(parts[name], name)
            removed[name] = (_PROPERTIES[name][2], 'office_properties', '')
        elif re.fullmatch(r'docProps/thumbnail\.(png|jpe?g)', name):
            removed[name] = ('http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail', 'office_preview', '')
        elif kind == 'pptx' and re.fullmatch(r'ppt/printerSettings/printerSettings[0-9]+\.bin', name):
            removed[name] = (R + '/printerSettings', 'office_printer_data', 'ppt/presentation.xml')
    for owner, entries in rels.items():
        if owner in removed and entries:
            raise ValueError('Metadata part owns embedded content')
        for rid, (target, reltype) in entries.items():
            if target not in removed:
                continue
            expected_type, _, expected_owner = removed[target]
            if owner != expected_owner or reltype != expected_type:
                raise ValueError('Unsupported reference to metadata')
            if owner:
                root = xml(parts[owner])
                if any(rid == node.get(attr) for node in root.iter()
                       for attr in (f'{{{R}}}id', f'{{{R}}}embed', f'{{{R}}}link')):
                    raise ValueError('Metadata referenced by rendered content')
    for name in sorted(removed):
        decisions.append(AncillaryDecision(structure=removed[name][1], disposition=AncillaryClass.STRIPPED))
    # Check complete content-type records before editing, including discarded ones.
    ct = xml(parts['[Content_Types].xml'])
    ns = 'http://schemas.openxmlformats.org/package/2006/content-types'
    if ct.tag != f'{{{ns}}}Types' or ct.attrib or ct.nsmap != {None: ns}:
        raise ValueError('Invalid content types')
    seen = set()
    for node in list(ct):
        fields = {'Extension', 'ContentType'} if node.tag == f'{{{ns}}}Default' else {'PartName', 'ContentType'}
        key = node.get('PartName') or node.get('Extension')
        if (node.tag not in {f'{{{ns}}}Default', f'{{{ns}}}Override'} or set(node.attrib) != fields
            or key in seen or len(node) or node.nsmap != {None: ns}
            or node.text and node.text.strip() or node.tail and node.tail.strip()):
            raise ValueError('Malformed content type record')
        seen.add(key)
        target = (node.get('PartName') or '').lstrip('/')
        if target in removed:
            expected = {'office_properties': {
                'docProps/core.xml': 'application/vnd.openxmlformats-package.core-properties+xml',
                'docProps/app.xml': 'application/vnd.openxmlformats-officedocument.extended-properties+xml',
                'docProps/custom.xml': 'application/vnd.openxmlformats-officedocument.custom-properties+xml',
            }.get(target), 'office_preview': 'image/png' if target.endswith('.png') else 'image/jpeg',
                'office_printer_data': 'application/vnd.openxmlformats-officedocument.presentationml.printerSettings'}[removed[target][1]]
            if node.get('ContentType') != expected or node.get('PartName') != '/' + target:
                raise ValueError('Invalid metadata content type')
            ct.remove(node)
    for name in list(parts):
        if name.endswith('.rels'):
            root = xml(parts[name])
            owner = '' if name == '_rels/.rels' else name.rsplit('/_rels/', 1)[0] + '/' + name.rsplit('/', 1)[1][:-5]
            for node in list(root):
                if rels[owner][node.get('Id')][0] in removed:
                    root.remove(node)
            parts[name] = serialize(root)
    parts['[Content_Types].xml'] = serialize(ct)
    for name in removed:
        del parts[name]
    # Remove user-supplied names/alternate descriptions without changing stable IDs.
    shape_tags = {f'{{{P}}}cNvPr', '{http://schemas.openxmlformats.org/drawingml/2006/picture}cNvPr',
                  '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr'}
    changed = False
    for name in list(parts):
        if (kind == 'docx' and name != 'word/document.xml' or kind == 'pptx' and
            not re.fullmatch(r'ppt/(slides/slide|notesSlides/notesSlide)[0-9]+\.xml', name)):
            continue
        root = xml(parts[name])
        for node in root.iter():
            if node.tag not in shape_tags:
                continue
            if not re.fullmatch(r'[0-9]+', node.get('id', '')) or 'name' not in node.attrib:
                raise ValueError('Invalid shape metadata')
            for attr in ('descr', 'title'):
                if attr in node.attrib:
                    del node.attrib[attr]
                    changed = True
            if node.get('name'):
                node.set('name', '')
                changed = True
        parts[name] = serialize(root)
    if changed:
        decisions.append(AncillaryDecision(structure='office_shape_metadata', disposition=AncillaryClass.SANITIZED))
    return AncillaryReport(decisions=tuple(decisions))


def validate_pdf_metadata(reader) -> AncillaryReport:
    """Permit removable scalar Info and well-formed document/page XMP only."""
    decisions = []
    if '/Info' in reader.trailer and not isinstance(reader.trailer['/Info'], NullObject):
        info = reader.trailer['/Info']
        scalar = (TextStringObject, ByteStringObject, NumberObject, FloatObject, BooleanObject, NullObject, NameObject)
        if not isinstance(info, DictionaryObject) or isinstance(info, StreamObject) or any(
            not isinstance(key, NameObject) or not isinstance(value, scalar) for key, value in info.items()):
            raise ValueError('Unsupported PDF properties payload')
        decisions.append(AncillaryDecision(structure='pdf_info', disposition=AncillaryClass.STRIPPED))
    for owner in [reader.trailer['/Root'], *reader.pages]:
        if '/Metadata' not in owner:
            continue
        stream = owner['/Metadata']
        if isinstance(stream, NullObject):
            continue  # A null structural key carries no metadata payload.
        if not isinstance(stream, StreamObject) or set(stream) - {'/Type', '/Subtype', '/Length', '/Filter'}:
            raise ValueError('Unsupported PDF metadata stream')
        if stream.get('/Type') != '/Metadata' or stream.get('/Subtype') != '/XML' or stream.get('/Filter') not in {None, '/FlateDecode'}:
            raise ValueError('Unsupported PDF metadata encoding')
        data = stream._data
        if stream.get('/Filter') == '/FlateDecode':
            decoder = zlib.decompressobj()
            data = decoder.decompress(data, 1024 * 1024 + 1)
            if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError('Invalid or oversized PDF metadata encoding')
        if len(data) > 1024 * 1024:
            raise ValueError('PDF metadata exceeds limit')
        root = ET.fromstring(data, ET.XMLParser(resolve_entities=False, no_network=True))
        if root.getroottree().docinfo.doctype or any(not isinstance(n.tag, str) for n in root.iter()):
            raise ValueError('Unsupported XMP declarations')
        if root.tag not in {'{adobe:ns:meta/}xmpmeta', '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'}:
            raise ValueError('Invalid XMP root')
        for direction in ('getprevious', 'getnext'):
            node = getattr(root, direction)()
            while node is not None:
                if not isinstance(node, ET._ProcessingInstruction) or node.target != 'xpacket':
                    raise ValueError('Unsupported XMP processing instruction')
                node = getattr(node, direction)()
        decisions.append(AncillaryDecision(structure='pdf_xmp', disposition=AncillaryClass.STRIPPED))
    return AncillaryReport(decisions=tuple(decisions))


def strip_pdf_metadata(document):
    document.set_metadata({})
    document.del_xml_metadata()
    document.xref_set_key(-1, 'Info', 'null')
    document.xref_set_key(-1, 'ID', 'null')  # Never carry original document identifiers.
    for page in document:
        if document.xref_get_key(page.xref, 'Metadata')[0] != 'null':
            document.xref_set_key(page.xref, 'Metadata', 'null')


def verify_encoded_image_metadata(data: bytes, output_format: str):
    """Accept only freshly encoded raster structures, not copied metadata chunks."""
    if output_format == 'PNG':
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Invalid sanitized PNG')
        cursor, tags = 8, []
        while cursor < len(data):
            length = struct.unpack_from('>I', data, cursor)[0]
            tag = data[cursor+4:cursor+8]
            end = cursor + 12 + length
            if end > len(data) or tag not in {b'IHDR', b'IDAT', b'IEND'}:
                raise ValueError('Metadata survived PNG encoding')
            expected = struct.unpack_from('>I', data, end-4)[0]
            if zlib.crc32(data[cursor+4:end-4]) & 0xffffffff != expected:
                raise ValueError('Invalid sanitized PNG checksum')
            tags.append(tag)
            cursor = end
        if len(tags) < 3 or tags[0] != b'IHDR' or tags[-1] != b'IEND' or any(t != b'IDAT' for t in tags[1:-1]):
            raise ValueError('Invalid sanitized PNG structure')
    elif output_format == 'JPEG':
        if not data.startswith(b'\xff\xd8') or not data.endswith(b'\xff\xd9'):
            raise ValueError('Invalid sanitized JPEG')
        cursor = 2
        while cursor < len(data)-2:
            if data[cursor] != 255:
                raise ValueError('Invalid JPEG record')
            tag = data[cursor+1]
            length = struct.unpack_from('>H', data, cursor+2)[0]
            end = cursor + 2 + length
            if length < 2 or end > len(data):
                raise ValueError('Invalid JPEG segment')
            if tag == 0xe0:
                if data[cursor+4:end] != b'JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00':
                    raise ValueError('Unsupported JPEG application data')
            elif tag not in {0xc0, 0xc4, 0xdb, 0xda}:
                raise ValueError('Metadata survived JPEG encoding')
            cursor = end
            if tag == 0xda:
                scan = data[cursor:-2]
                if re.search(b'\xff[^\x00\xd0-\xd7]', scan):
                    raise ValueError('Unexpected JPEG scan payload')
                return AncillaryReport(decisions=(AncillaryDecision(
                    structure='image_metadata', disposition=AncillaryClass.SANITIZED),))
        raise ValueError('Missing sanitized JPEG scan')
    else:
        raise ValueError('Unsupported sanitized image encoding')
    return AncillaryReport(decisions=(AncillaryDecision(
        structure='image_metadata', disposition=AncillaryClass.SANITIZED),))

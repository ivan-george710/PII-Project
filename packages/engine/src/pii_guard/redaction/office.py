"""Private, conservative OOXML rewriting primitives and structure validation."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from uuid import UUID
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import os
import posixpath
import re
import struct

from docx import Document
from pptx import Presentation
from lxml import etree as ET
from PIL import Image

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import ExtractedTextBlock, SanitizedArtifact, SourceLocation
from pii_guard.redaction.image import redact_image, _source_key
from pii_guard.redaction.text import REPLACEMENT, _merge_spans, redact_text
from pii_guard.redaction.metadata import AncillaryClass, classify_office_part
from pii_guard.rules.policy import RedactionTarget

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'


def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Unsupported XML declarations')
    root = ET.fromstring(data, ET.XMLParser(resolve_entities=False, no_network=True,
        remove_comments=False, remove_pis=False))
    if root.getroottree().docinfo.doctype:
        raise ValueError('Unsupported XML document type')
    if root.getprevious() is not None or root.getnext() is not None:
        raise ValueError('Unsupported XML outside the document root')
    if any(not isinstance(n.tag, str) for n in root.iter()):
        raise ValueError('Unsupported XML comments or processing instructions')
    return root


def serialize(root):
    return ET.tostring(root, encoding='UTF-8', xml_declaration=True, standalone=True)


_TAGS = {
    W: set('document body p pPr r rPr t tab br cr b bCs i iCs u color sz szCs rFonts highlight pStyle spacing jc ind keepNext keepLines contextualSpacing tbl tblPr tblStyle tblW tblLook tblGrid gridCol tr trPr tc tcPr tcW gridSpan vMerge vAlign sectPr pgSz pgMar cols docGrid drawing'.split()),
    A: set('graphic graphicData graphicFrameLocks masterClrMapping blip blipFill stretch fillRect xfrm off ext chOff chExt prstGeom avLst bodyPr lstStyle p pPr r rPr t br endParaRPr solidFill noFill srgbClr schemeClr latin ea cs spAutoFit noAutofit normAutofit ln effectLst spLocks picLocks'.split()),
    P: set('sld notes cSld spTree nvGrpSpPr cNvPr cNvGrpSpPr nvPr grpSpPr sp nvSpPr cNvSpPr spPr txBody clrMapOvr masterClrMapping ph pic nvPicPr cNvPicPr blipFill'.split()),
    'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing': set('inline extent effectExtent docPr cNvGraphicFramePr'.split()),
    'http://schemas.openxmlformats.org/drawingml/2006/picture': set('pic nvPicPr cNvPr cNvPicPr blipFill spPr'.split()),
}
_ATTRS = set('id name descr typeface val space rsidR rsidRPr rsidSect w h top right bottom left header footer gutter linePitch distT distB distL distR cx cy x y l t r b noChangeAspect uri embed cstate prst type idx sz txBox noGrp wrap anchor anchorCtr rtlCol rot flipH flipV after before line lineRule ascii hAnsi eastAsia cs asciiTheme hAnsiTheme eastAsiaTheme cstheme firstLine hanging num start end fill themeColor themeTint themeShade firstRow lastRow firstColumn lastColumn noHBand noVBand algn marL marR indent lvl defTabSz rtl eaLnBrk latinLnBrk hangingPunct kern lang altLang u strike baseline dirty smtClean fontScale lnSpcReduction orientation'.split())
_ENUMS = set('true false preserve auto single double none left right center both start end top bottom baseline clear continuous pct dxa atLeast exact leftToRight tb lrTb rect roundRect ellipse screen4x3 screen16x9 body title ctrTitle subTitle sldImg sldNum quarter half full square t ctr b l r just low med high compressed print tx1 tx2 bg1 bg2 accent1 accent2 accent3 accent4 accent5 accent6 hlink folHlink minorHAnsi majorHAnsi minorEastAsia majorEastAsia minorBidi majorBidi default en-US +mn-lt +mn-ea +mn-cs +mj-lt +mj-ea +mj-cs black white yellow green cyan magenta blue red darkBlue darkCyan darkGreen darkMagenta darkRed darkYellow darkGray lightGray'.split())


def inspect_editable(root, kind):
    style_ids = {n.get(f'{{{W}}}styleId') for n in xml(template('docx')['word/styles.xml']).iter(f'{{{W}}}style')}
    namespaces = dict(xml(template(kind)['word/document.xml' if kind == 'docx' else 'ppt/slides/slide1.xml']).nsmap)
    namespaces.update({'a': A, 'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'})
    for n in root.iter():
        if any(namespaces.get(prefix) != uri for prefix, uri in n.nsmap.items()):
            raise ValueError('Unsupported namespace declaration')
        q = ET.QName(n)
        if kind == 'pptx' and q.namespace not in {P, A} or kind == 'docx' and q.namespace == P:
            raise ValueError('Unsupported XML namespace')
        if q.localname not in _TAGS.get(q.namespace, set()):
            raise ValueError('Unsupported Office XML content')
        if n.text and n.text.strip() and n.tag not in {f'{{{W}}}t', f'{{{A}}}t'}:
            raise ValueError('Unsupported text payload')
        if n.tail and n.tail.strip():
            raise ValueError('Unsupported XML tail payload')
        if q.localname == 't':
            ns = W if kind == 'docx' else A
            if q.namespace != ns or n.getparent().tag != f'{{{ns}}}r' or n.getparent().getparent().tag != f'{{{ns}}}p':
                raise ValueError('Text outside an ordinary paragraph run')
        if n.tag in {f'{{{W}}}p', f'{{{A}}}p'}:
            if any(parent.tag == n.tag for parent in n.iterancestors()):
                raise ValueError('Unsupported nested paragraph')
            if kind == 'pptx' and not any(parent.tag == f'{{{P}}}txBody' for parent in n.iterancestors()):
                raise ValueError('Text outside a shape text body')
        if n.tag in {f'{{{W}}}tab', f'{{{W}}}br', f'{{{W}}}cr'} and n.getparent().tag != f'{{{W}}}r':
            raise ValueError('Unsupported text control placement')
        if n.tag in {f'{{{W}}}sz', f'{{{W}}}szCs'} and int(n.get(f'{{{W}}}val', '0')) <= 0:
            raise ValueError('Hidden zero-size text')
        if n.tag in {f'{{{A}}}rPr', f'{{{A}}}endParaRPr'} and 'sz' in n.attrib and int(n.get('sz')) <= 0:
            raise ValueError('Hidden zero-size text')
        if n.tag in {f'{{{W}}}color', f'{{{W}}}highlight', f'{{{A}}}srgbClr'}:
            if n.get(f'{{{W}}}val', n.get('val', '')).lower() in {'ffffff', 'white'}:
                raise ValueError('Unsupported invisible text styling')
        if n.tag == f'{{{A}}}noFill' and any(parent.tag == f'{{{A}}}rPr' for parent in n.iterancestors()):
            raise ValueError('Invisible text fill')
        for key, value in n.attrib.items():
            aq = ET.QName(key)
            local = aq.localname
            if key == '{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable' and n is root and kind == 'docx' and value == 'w14 wp14':
                continue
            if aq.namespace not in {None, W, R, 'http://www.w3.org/XML/1998/namespace'} or local not in _ATTRS:
                raise ValueError('Unsupported Office attribute')
            if local == 'name':
                if not re.fullmatch(r'(?:|image\.(?:png|jpe?g)|(?:Picture|TextBox|Rectangle|Title|Subtitle|Content Placeholder|Slide Image Placeholder|Notes Placeholder|Slide Number Placeholder) [0-9]+)', value):
                    raise ValueError('Unsupported descriptive metadata')
            elif local == 'descr':
                if value not in {'image.png', 'image.jpg', 'image.jpeg'}:
                    raise ValueError('Unsupported alternative text')
            elif aq.namespace == R:
                if not re.fullmatch(r'rId[0-9]+', value):
                    raise ValueError('Invalid image relationship')
            elif local == 'uri':
                if value != 'http://schemas.openxmlformats.org/drawingml/2006/picture':
                    raise ValueError('Unsupported drawing payload')
            elif local in {'ascii', 'hAnsi', 'eastAsia', 'cs', 'typeface'}:
                if value not in {'Calibri', 'Arial', 'Times New Roman', 'Cambria', 'Courier New', 'Symbol'} | _ENUMS:
                    raise ValueError('Unsupported font data')
            elif value not in _ENUMS | style_ids and not re.fullmatch(r'-?[0-9]+|[0-9A-Fa-f]{4,8}', value):
                raise ValueError('Unsupported attribute value')
            if local in {'rot', 'flipH', 'flipV'} and value not in {'0', 'false'}:
                raise ValueError('Unsupported transformed content')


def unpack(data):
    if not isinstance(data, bytes) or len(data) > 25 * 1024 * 1024:
        raise ValueError('Invalid Office input')
    if not data.startswith(b'PK\x03\x04') or data[-22:-18] != b'PK\x05\x06' or data[-2:] != b'\x00\x00':
        raise ValueError('Unsupported archive prefix or trailing payload')
    with ZipFile(BytesIO(data)) as package:
        infos = package.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or len(names) > 2000 or package.comment:
            raise ValueError('Ambiguous Office package')
        if sum(i.file_size for i in infos) > 100 * 1024 * 1024:
            raise ValueError('Expanded package exceeds limit')
        for i in infos:
            name = i.filename
            if (i.flag_bits & 1 or i.is_dir() or i.comment or i.extra or '\\' in name
                or name.startswith('/') or posixpath.normpath(name) != name
                or any(c in name for c in ('%', ':', '\x00')) or name.startswith('../')):
                raise ValueError('Unsupported package entry')
        cursor = 0
        for i in sorted(infos, key=lambda entry: entry.header_offset):
            if i.header_offset != cursor or i.flag_bits & ~0x800:
                raise ValueError('Unsupported archive layout')
            header = struct.unpack_from('<4s5H3I2H', data, cursor)
            name_size, extra_size = header[-2:]
            if header[0] != b'PK\x03\x04' or extra_size or header[8] != i.file_size or header[7] != i.compress_size:
                raise ValueError('Ambiguous local archive record')
            name_bytes = data[cursor+30:cursor+30+name_size]
            if name_bytes.decode('utf-8' if i.flag_bits & 0x800 else 'cp437') != i.filename:
                raise ValueError('Archive name mismatch')
            cursor += 30 + name_size + extra_size + i.compress_size
        if cursor != package.start_dir:
            raise ValueError('Unsupported data between archive records')
        parts = {i.filename: package.read(i) for i in infos}
        # No Office-library parser sees untrusted XML before entity/DTD checks.
        for name, content in parts.items():
            if name.endswith(('.xml', '.rels')):
                xml(content)
        return parts


def pack(parts):
    # Fresh ZIP: no old entries, comments, extra fields or appended revisions.
    with BytesIO() as stream:
        with ZipFile(stream, 'w', ZIP_DEFLATED) as package:
            for name in sorted(parts):
                entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = ZIP_DEFLATED
                package.writestr(entry, parts[name])
        return stream.getvalue()


@lru_cache(maxsize=2)
def template(kind):
    obj = Document() if kind == 'docx' else Presentation()
    if kind == 'pptx':
        obj.slides.add_slide(obj.slide_layouts[6]).notes_slide
    stream = BytesIO()
    obj.save(stream)
    return unpack(stream.getvalue())


def relationships(parts):
    result = {}
    for name, data in parts.items():
        if not name.endswith('.rels'):
            continue
        root = xml(data)
        if root.tag != f'{{{REL}}}Relationships' or root.attrib or root.nsmap != {None: REL}:
            raise ValueError('Invalid relationships')
        owner = '' if name == '_rels/.rels' else str(PurePosixPath(name).parent.parent / PurePosixPath(name).name[:-5])
        mapping = {}
        for rel in root:
            if rel.tag != f'{{{REL}}}Relationship' or set(rel.attrib) != {'Id', 'Type', 'Target'} or len(rel) or rel.nsmap != {None: REL}:
                raise ValueError('External or unsupported relationship')
            rid, target, reltype = rel.get('Id'), rel.get('Target'), rel.get('Type')
            if not re.fullmatch(r'rId[0-9]+', rid) or rid in mapping or any(c in target for c in ('%', '\\', ':', '#', '?')):
                raise ValueError('Invalid relationship reference')
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(owner), target))
            if resolved not in parts or resolved.startswith('../'):
                raise ValueError('Missing relationship part')
            mapping[rid] = (resolved, reltype)
        if any(n.text and n.text.strip() or n.tail and n.tail.strip() for n in root.iter()):
            raise ValueError('Unexpected relationship text')
        result[owner] = mapping
    # Unreferenced parts are also checked by the caller, never silently dropped.
    return result


def inspect_package(parts, kind, editable, rels):
    defaults = template(kind)
    for name, data in parts.items():
        # Supported metadata is already stripped. Any remaining custom ancillary
        # content must be proven safe structural data or fail explicitly.
        decision = classify_office_part(name, data, defaults, editable, kind)
        if decision.disposition == AncillaryClass.UNSUPPORTED:
            raise ValueError('Unsupported ancillary content')
    default_rels = relationships(defaults)
    for owner, entries in rels.items():
        if owner not in editable and owner not in {'', 'ppt/presentation.xml'}:
            if entries != default_rels.get(owner):
                raise ValueError('Modified ancillary relationships')
        for rid, (target, reltype) in entries.items():
            stock = default_rels.get(owner, {}).get(rid)
            if stock == (target, reltype):
                continue
            suffix = reltype.removeprefix(R + '/')
            if suffix == 'image' and owner in editable and '/media/' in target:
                continue
            if kind == 'pptx' and suffix in {'slide', 'notesSlide', 'notesMaster', 'slideLayout'}:
                valid = ((owner == 'ppt/presentation.xml' and suffix in {'slide', 'notesMaster'})
                    or (owner in editable and suffix in {'slide', 'notesSlide', 'notesMaster', 'slideLayout'}))
                directory = {'slide': 'slides/slide', 'notesSlide': 'notesSlides/notesSlide',
                    'notesMaster': 'notesMasters/notesMaster', 'slideLayout': 'slideLayouts/slideLayout'}[suffix]
                if valid and re.fullmatch('ppt/' + directory + r'[0-9]+\.xml', target):
                    continue
            raise ValueError('Unsupported relationship')
    # Content types cannot introduce macros, alternate payloads, or unknown parts.
    ct = xml(parts['[Content_Types].xml'])
    ns = 'http://schemas.openxmlformats.org/package/2006/content-types'
    if ct.tag != f'{{{ns}}}Types' or ct.attrib or ct.nsmap != {None: ns}:
        raise ValueError('Invalid content types')
    allowed_types = {n.get('ContentType') for n in xml(defaults['[Content_Types].xml'])} | {'image/png', 'image/jpeg'}
    default_ct = xml(defaults['[Content_Types].xml'])
    stock_extensions = {n.get('Extension') for n in default_ct if n.tag.endswith('Default')}
    seen = set()
    for node in ct:
        key = node.get('PartName') or node.get('Extension')
        if node.tag not in {f'{{{ns}}}Default', f'{{{ns}}}Override'} or key in seen or node.get('ContentType') not in allowed_types:
            raise ValueError('Unsupported content type')
        if node.nsmap != {None: ns} or len(node):
            raise ValueError('Unsupported content type payload')
        if set(node.attrib) != ({'Extension', 'ContentType'} if node.tag.endswith('Default') else {'PartName', 'ContentType'}):
            raise ValueError('Invalid content type attributes')
        if node.tag.endswith('Override') and key.lstrip('/') not in parts:
            raise ValueError('Missing content part')
        if node.tag.endswith('Default') and key not in stock_extensions | {'png', 'jpg', 'jpeg'}:
            raise ValueError('Unknown content extension')
        if node.tag.endswith('Override') and key != '/' + key.lstrip('/'):
            raise ValueError('Invalid content part name')
        seen.add(key)
    if any(n.text and n.text.strip() or n.tail and n.tail.strip() for n in ct.iter()):
        raise ValueError('Unexpected content type text')
    extensions = {n.get('Extension'): n.get('ContentType') for n in ct if n.tag.endswith('Default')}
    overrides = {n.get('PartName').lstrip('/'): n.get('ContentType') for n in ct if n.tag.endswith('Override')}
    stock_ext = {n.get('Extension'): n.get('ContentType') for n in default_ct if n.tag.endswith('Default')}
    stock_parts = {n.get('PartName').lstrip('/'): n.get('ContentType') for n in default_ct if n.tag.endswith('Override')}
    for name in parts:
        if name == '[Content_Types].xml':
            continue
        extension = name.rsplit('.', 1)[-1]
        actual = overrides.get(name, extensions.get(extension))
        expected = stock_parts.get(name, stock_ext.get(extension))
        if '/media/' in name:
            expected = 'image/png' if extension == 'png' else 'image/jpeg'
        elif name in editable and kind == 'pptx':
            expected = 'application/vnd.openxmlformats-officedocument.presentationml.' + ('notesSlide+xml' if '/notesSlides/' in name else 'slide+xml')
        if actual != expected:
            raise ValueError('Content type disagrees with the part')


def paragraph_units(root, namespace):
    units = []
    for p in root.iter(f'{{{namespace}}}p'):
        nodes = []
        def visit(node):
            if node.tag == f'{{{namespace}}}t':
                nodes.append((node, node.text or ''))
            elif node.tag == f'{{{namespace}}}tab':
                nodes.append((node, '\t'))
            elif node.tag in {f'{{{namespace}}}br', f'{{{namespace}}}cr'}:
                nodes.append((node, '\n'))
            for child in node:
                if child.tag != f'{{{namespace}}}p':
                    visit(child)
        visit(p)
        if nodes:
            units.append((p, nodes, ''.join(t for _, t in nodes)))
    return units


def rewrite_unit(nodes, text, targets, source, namespace):
    expected = redact_text(text, targets, source=source)
    spans = _merge_spans([(t.location.start, t.location.end) for t in targets])
    cursor = 0
    for node, value in nodes:
        start, end = cursor, cursor + len(value)
        pieces = []
        local = start
        for lo, hi in spans:
            if hi <= start or lo >= end:
                continue
            pieces.append(text[local:max(local, lo)])
            if start <= lo < end:
                pieces.append(REPLACEMENT)
            local = max(local, min(end, hi))
        pieces.append(text[local:end])
        rendered = ''.join(pieces)
        if rendered != value:
            if node.tag != f'{{{namespace}}}t':
                if not rendered:
                    node.getparent().remove(node)
                else:
                    replacement = ET.Element(f'{{{namespace}}}t')
                    replacement.text = rendered
                    replacement.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                    if namespace == A:
                        run = ET.Element(f'{{{A}}}r')
                        run.append(replacement)
                        replacement = run
                    node.getparent().replace(node, replacement)
            else:
                node.text = rendered
                node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        cursor = end
    # Verify against the reusable codepoint renderer after distributing runs.
    # Empty runs retain their original formatting, never their old payload.
    return expected


def validate_inputs(artifact_id, blocks, targets, native, images, region_sources=()):
    if not isinstance(artifact_id, UUID):
        raise ValueError('Invalid artifact identity')
    known = {}
    for block in blocks:
        if not isinstance(block, ExtractedTextBlock):
            raise ValueError('Invalid original extraction')
        block = ExtractedTextBlock.model_validate(block.model_dump(warnings=False))
        loc = block.location
        if loc.artifact_id != artifact_id or loc.page_number is not None or loc.source_ref in known:
            raise ValueError('Mismatched original extraction')
        if loc.kind == 'native_text':
            unit = native.get(loc.source_ref)
            if unit is None or unit[2] != block.text or unit[3] != loc.slide_number or loc.bbox is not None:
                raise ValueError('Original text or source changed')
        else:
            ref, sep, index = loc.source_ref.rpartition(':ocr:')
            image = images.get(ref)
            if not sep or not index.isascii() or not index.isdigit() or image is None or image[1] != loc.slide_number:
                raise ValueError('Unmapped original OCR block')
        known[loc.source_ref] = block
    from types import SimpleNamespace
    for source in region_sources:
        loc = SourceLocation.model_validate(source.model_dump())
        base, sep, index = loc.source_ref.rpartition(':face:')
        if loc.kind != 'face' or loc.artifact_id != artifact_id or loc.page_number is not None or not sep or not index.isascii() or not index.isdigit() or base not in images or images[base][1] != loc.slide_number or loc.source_ref in known:
            raise ValueError('Unmapped original face region')
        known[loc.source_ref] = SimpleNamespace(location=loc)
    grouped = defaultdict(list)
    for target in targets:
        if not isinstance(target, RedactionTarget):
            raise ValueError('Expected enabled private target')
        target = RedactionTarget.model_validate(target.model_dump(warnings=False))
        loc = target.location
        block = known.get(loc.source_ref)
        if block is None or _source_key(loc) != _source_key(block.location) or loc.bbox != block.location.bbox:
            raise ValueError('Unrecognized target source')
        if loc.kind != "face" and not 0 <= loc.start < loc.end <= len(block.text):
            raise ValueError('Invalid original span')
        grouped[loc.source_ref].append(target)
    return known, grouped


def rewrite_media(parts, images, known, grouped, artifact_id):
    # One union per underlying media resource: every repeated use sees safe pixels.
    targets_by_media = defaultdict(list)
    sources_by_media = defaultdict(list)
    used_media = {image[0] for image in images.values()}
    for ref, block in known.items():
        if block.location.kind not in {'ocr', 'face'}:
            continue
        image_ref = ref.rpartition(':face:' if block.location.kind == 'face' else ':ocr:')[0]
        media, slide, placement = images[image_ref]
        loc = block.location
        if placement is None:
            bbox = loc.bbox
        else:
            x, y, w, h = placement
            bx, by, bw, bh = loc.bbox
            vals = ((bx-x)/w, (by-y)/h, bw/w, bh/h)
            if vals[0] < -1e-9 or vals[1] < -1e-9 or vals[0]+vals[2] > 1+1e-9 or vals[1]+vals[3] > 1+1e-9:
                raise ValueError('OCR outside its picture placement')
            left, top = max(0, vals[0]), max(0, vals[1])
            bbox = (left, top, min(vals[2], 1-left), min(vals[3], 1-top))
        local_ref = 'image' if loc.kind == 'face' else f'image:ocr:{len(sources_by_media[media])}'
        source = loc.model_copy(update={'source_ref': local_ref, 'slide_number': None, 'bbox': bbox})
        source = SourceLocation.model_validate(source.model_dump())
        sources_by_media[media].append(source)
        for target in grouped.get(ref, ()):
            targets_by_media[media].append(RedactionTarget(finding_id=target.finding_id,
                location=source.model_copy(update={'start': target.location.start, 'end': target.location.end})))
    all_media = {name for name in parts if '/media/' in name}
    if all_media != used_media:
        raise ValueError('Hidden or unplaced media')
    for media in sorted(used_media):
        with Image.open(BytesIO(parts[media])) as image:
            if image.getexif().get(274, 1) != 1:
                raise ValueError('Unsupported Office image orientation')
            expected = 'PNG' if media.endswith('.png') else 'JPEG'
            if image.format != expected:
                raise ValueError('Image encoding disagrees with package')
        parts[media] = redact_image(parts[media], targets_by_media[media], artifact_id=artifact_id,
            sources=sources_by_media[media], image_ref='image', output_format=expected).data


def publish(renderer, kind, source_path, output_path, targets, *, artifact_id, blocks=(), submission_id=None):
    temporary = None
    published = False
    try:
        source_path, output_path = Path(source_path), Path(output_path)
        if (source_path.resolve() == output_path.resolve() or output_path.exists()
            or not source_path.is_file() or source_path.stat().st_size > 25 * 1024 * 1024):
            raise ValueError('Invalid input or destination')
        data = renderer(source_path.read_bytes(), targets, artifact_id=artifact_id,
            blocks=blocks, submission_id=submission_id)
        result = SanitizedArtifact(artifact_id=artifact_id, filename=output_path.name,
            mime_type=f'application/vnd.openxmlformats-officedocument.{"wordprocessingml.document" if kind == "docx" else "presentationml.presentation"}',
            output_path=output_path.resolve(), size_bytes=len(data), sha256=sha256(data).hexdigest(), format_changed=False)
        with NamedTemporaryFile(dir=output_path.parent, prefix='.pii-redaction-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output_path)
        published = True
        return result
    except Exception:
        raise failure(kind, artifact_id, submission_id) from None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except Exception:
                if published:
                    try:
                        output_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                raise failure(kind, artifact_id, submission_id) from None


def failure(kind, artifact_id, submission_id):
    return ProcessingError(ProcessingErrorCode.REDACTION_FAILED,
        f'{kind.upper()} redaction failed: unsupported content or invalid original sources.',
        artifact_id=artifact_id if isinstance(artifact_id, UUID) else None,
        submission_id=submission_id if isinstance(submission_id, UUID) else None)

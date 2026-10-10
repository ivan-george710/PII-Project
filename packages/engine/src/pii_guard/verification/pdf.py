"""Independent serialized PDF checks and underlying image/render inspection."""
from functools import lru_cache
from io import BytesIO
from math import ceil, floor
import zlib

import pymupdf
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NullObject, ContentStream, NameObject, NumberObject, StreamObject

from .evidence import digest, expected_text
from .raster import image_evidence, check_pixels, pixel_rect


def canonical(text):
    # PDF text extraction whitespace changes after content-stream cleanup.
    return ''.join(char for char in text if not char.isspace())


def geometry(page):
    return (tuple(page.mediabox),tuple(page.cropbox),page.rotation)


def prepare(data,artifact_id,blocks,targets):
    from pii_guard.redaction.pdf import _inspect_structure
    reader=PdfReader(BytesIO(data),strict=True)
    _inspect_structure(reader)  # Input support policy only; never checks output.
    grouped={}
    for target in targets: grouped.setdefault(target.location.page_number,[]).append(target.location)
    with pymupdf.open(stream=data,filetype='pdf') as doc:
        if doc.is_repaired or doc.page_count!=len(reader.pages): raise ValueError('Invalid original PDF')
        for ref,block in blocks.items():
            loc=block.location
            if not loc.page_number or loc.page_number>doc.page_count or loc.slide_number is not None:
                raise ValueError('Invalid original PDF source')
            if loc.kind=='native_text':
                if ref!=f'pdf:page:{loc.page_number}:native_text' or block.text!=(reader.pages[loc.page_number-1].extract_text() or '') or loc.bbox is not None:
                    raise ValueError('Changed original native source')
            elif not ref.startswith(f'pdf:page:{loc.page_number}:rendered:ocr:') or not ref.rsplit(':',1)[1].isascii() or not ref.rsplit(':',1)[1].isdigit():
                raise ValueError('Wrong rendered OCR source')
        pages=[]
        for number,page in enumerate(doc,1):
            text=reader.pages[number-1].extract_text() or ''
            chars=[]
            for block in page.get_text('rawdict')['blocks']:
                if block['type']==0:
                    for line in block['lines']:
                        for span in line['spans']:
                            chars.extend((char['c'],tuple(char['bbox'])) for char in span['chars'] if not char['c'].isspace())
            if canonical(text)!=''.join(char for char,_ in chars): raise ValueError('Unmappable PDF glyph order')
            offset_map=dict(zip((i for i,c in enumerate(text) if not c.isspace()),chars,strict=True))
            rects=[]
            for loc in grouped.get(number,()):
                if loc.kind=='native_text':
                    rects.extend(rect for i,(_,rect) in offset_map.items() if loc.start<=i<loc.end)
                else:
                    if loc.kind=='face' and loc.source_ref!=f'pdf:page:{number}:rendered': raise ValueError('Wrong face source')
                    x,y,w,h=loc.bbox
                    rect=pymupdf.Rect(x*page.rect.width,y*page.rect.height,(x+w)*page.rect.width,(y+h)*page.rect.height)
                    rects.append(tuple(rect*page.derotation_matrix))
            # Account for enabled regions removing intersecting glyphs, including
            # overlaps with disabled matches; verify the complete page afterward.
            retained=''.join(char for char,box in chars if not any(
                not (pymupdf.Rect(box)&pymupdf.Rect(rect)).is_empty for rect in rects))
            image_plans=[]
            for item in page.get_image_info(xrefs=True):
                a,b,c,d,_,_=item['transform']
                if b or c or a<=0 or d<=0: raise ValueError('Unsupported original placement')
                placement=pymupdf.Rect(item['bbox']);boxes=[]
                for rect in rects:
                    intersection=placement&pymupdf.Rect(rect)
                    if not intersection.is_empty:
                        boxes.append(((intersection.x0-placement.x0)/placement.width,
                            (intersection.y0-placement.y0)/placement.height,
                            intersection.width/placement.width,intersection.height/placement.height))
                image_data=doc.extract_image(item['xref'])['image']
                image_plans.append((tuple(placement),image_evidence(image_data,(artifact_id,number,tuple(placement)),boxes)))
            pages.append((geometry(page),digest((artifact_id,number,'native'),retained),
                tuple(sorted(set(rects))),tuple(image_plans)))
        return tuple(pages)


@lru_cache(maxsize=1)
def _generated_profile():
    # Generate a harmless library-owned RGB profile, independently of any writer
    # output. Only this exact profile is safe structural ICC content.
    b=BytesIO();Image.new('RGB',(1,1),'white').save(b,format='PNG')
    with pymupdf.open() as doc:
        page=doc.new_page();page.insert_image(pymupdf.Rect(0,0,1,1),stream=b.getvalue())
        reader=PdfReader(BytesIO(doc.tobytes()))
        for image in reader.pages[0]['/Resources']['/XObject'].values():
            space=image.get_object()['/ColorSpace']
            if isinstance(space,ArrayObject) and space[0]=='/ICCBased':
                return digest('generated-rgb-profile',space[1].get_object().get_data())
    return None


def _keys(value,allowed):
    if not isinstance(value,DictionaryObject) or set(value)-set(allowed.split()):
        raise ValueError('Unsupported serialized PDF object')


def _bounded_stream(stream):
    filters=stream.get('/Filter')
    if isinstance(filters,ArrayObject):
        if len(filters)!=1:raise ValueError('Unsupported verification stream encoding')
        filters=filters[0]
    data=stream._data
    if filters=='/FlateDecode':
        decoder=zlib.decompressobj();data=decoder.decompress(data,64*1024*1024+1)
        if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
            raise ValueError('Invalid or excessive verification stream')
    elif filters not in {None,'/DCTDecode'}:raise ValueError('Unsupported verification stream encoding')
    if len(data)>64*1024*1024:raise ValueError('Verification stream limit')
    return data


def structure(reader,doc):
    if reader.is_encrypted or doc.is_repaired or '/Prev' in reader.trailer or '/XRefStm' in reader.trailer:
        raise ValueError('Unsupported sanitized PDF')
    _keys(reader.trailer,'/Root /Size /ID /Info')
    if reader.metadata: raise ValueError('Info survived')
    root=reader.trailer['/Root']
    _keys(root,'/Type /Pages /Version /PageMode /PageLayout')
    if root.get('/Type')!='/Catalog': raise ValueError('Invalid catalog')
    enums={'/Version':{f'/1.{n}' for n in range(8)}|{'/2.0'},
        '/PageMode':{'/UseNone','/UseOutlines','/UseThumbs','/FullScreen','/UseOC','/UseAttachments'},
        '/PageLayout':{'/SinglePage','/OneColumn','/TwoColumnLeft','/TwoColumnRight','/TwoPageLeft','/TwoPageRight'}}
    for key,values in enums.items():
        if key in root and (not isinstance(root[key],NameObject) or root[key] not in values): raise ValueError('Invalid preference')
    allowed_ops=set(b"q Q cm BT ET Tf Tj TJ Td TD Tm T* Tc Tw Tz TL Tr Ts ' \" g G rg RG k K w J j M d ri i m l c v y h re S s f F f* B B* b b* n Do".split())
    reachable=set()
    def walk(value):
        if isinstance(value,IndirectObject):
            if value.idnum in reachable:return
            reachable.add(value.idnum);walk(value.get_object())
        elif isinstance(value,DictionaryObject):
            for child in value.values():walk(child)
        elif isinstance(value,(ArrayObject,list)):
            for child in value:walk(child)
    walk(reader.trailer)
    payloads=[];expanded=0
    for xref in range(1,doc.xref_length()):
        value=doc.xref_object(xref)
        if value.strip()!='null' and xref not in reachable: raise ValueError('Obsolete or unreferenced object')
        payloads.append(value.encode())
        if doc.xref_is_stream(xref):
            stream=reader.get_object(IndirectObject(xref,0,reader))
            if not isinstance(stream,StreamObject):raise ValueError('Inconsistent stream parser')
            decoded=_bounded_stream(stream);expanded+=len(decoded)
            if expanded>100*1024*1024:raise ValueError('Expanded PDF verification limit')
            payloads.append(decoded)
    # Inspect intermediate page tree nodes as well as flattened pages.
    seen=set()
    def tree(node):
        node=node.get_object()
        if id(node) in seen: raise ValueError('Cyclic page tree')
        seen.add(id(node))
        if node.get('/Type')=='/Pages':
            _keys(node,'/Type /Kids /Count /Parent /MediaBox /CropBox /Rotate /Resources')
            if not isinstance(node['/Type'],NameObject) or not isinstance(node.get('/Count'),NumberObject) or node['/Count']<1:
                raise ValueError('Invalid page tree fields')
            if '/Resources' in node: resources(node['/Resources'])
            for child in node['/Kids']: tree(child)
        elif node.get('/Type')!='/Page': raise ValueError('Invalid page tree')
    def resources(res):
        res=res.get_object()
        _keys(res,'/Font /XObject /ProcSet')
        if any(item not in {'/PDF','/Text','/ImageB','/ImageC','/ImageI'} for item in res.get('/ProcSet',[])): raise ValueError('Unknown procset')
        fonts=res.get('/Font',{});fonts=fonts.get_object() if hasattr(fonts,'get_object') else fonts
        for resource,font in fonts.items():
            font=font.get_object();_keys(font,'/Type /Subtype /BaseFont /Encoding /Name')
            if '/Type' in font and (not isinstance(font['/Type'],NameObject) or font['/Type']!='/Font'):
                raise ValueError('Invalid font type')
            families={'Helvetica','Times-Roman','Courier','Symbol','ZapfDingbats','Helvetica-Bold','Helvetica-Oblique','Helvetica-BoldOblique',
                'Times-Bold','Times-Italic','Times-BoldItalic','Courier-Bold','Courier-Oblique','Courier-BoldOblique'}
            if font.get('/Subtype')!='/Type1' or str(font.get('/BaseFont'))[1:] not in families: raise ValueError('Unsupported font')
            if font.get('/Encoding','/WinAnsiEncoding') not in {'/WinAnsiEncoding','/MacRomanEncoding'}: raise ValueError('Unsupported encoding')
            if '/Name' in font and (not isinstance(font['/Name'],NameObject) or font['/Name']!=resource): raise ValueError('Font payload')
        images=res.get('/XObject',{});images=images.get_object() if hasattr(images,'get_object') else images
        for image in images.values():
            image=image.get_object();_keys(image,'/Type /Subtype /Width /Height /ColorSpace /BitsPerComponent /Filter /DecodeParms /Length')
            if '/Type' in image and (not isinstance(image['/Type'],NameObject) or image['/Type']!='/XObject'):
                raise ValueError('Invalid image type')
            if image.get('/Subtype')!='/Image' or image.get('/BitsPerComponent')!=8: raise ValueError('Unsupported XObject')
            space=image['/ColorSpace']
            if isinstance(space,ArrayObject):
                if len(space)!=2 or space[0]!='/ICCBased':raise ValueError('Unsupported color space')
                profile=space[1].get_object();_keys(profile,'/N /Alternate /Length /Filter')
                if profile.get('/N')!=3 or digest('generated-rgb-profile',profile.get_data())!=_generated_profile(): raise ValueError('Untrusted profile')
            elif space not in {'/DeviceRGB','/DeviceGray'}:raise ValueError('Unknown color space')
            filters=image.get('/Filter',[]);filters=filters if isinstance(filters,list) else [filters]
            if any(f not in {'/FlateDecode','/DCTDecode','/ASCII85Decode'} for f in filters):raise ValueError('Unsupported image filter')
            if image.get('/DecodeParms'):_keys(image['/DecodeParms'],'/Predictor /Columns /Colors /BitsPerComponent')
    tree(root['/Pages'])
    for page in reader.pages:
        _keys(page,'/Type /Parent /MediaBox /CropBox /Rotate /Resources /Contents /BleedBox /TrimBox /ArtBox /Annots /Metadata /Trans')
        if not isinstance(page.get('/Type'),NameObject) or page['/Type']!='/Page':raise ValueError('Invalid page type')
        if '/Trans' in page and not isinstance(page['/Trans'],NullObject) and page['/Trans']!={}:raise ValueError('Transition survived')
        if '/Metadata' in page and not isinstance(page['/Metadata'],NullObject):raise ValueError('XMP survived')
        if '/Annots' in page and not isinstance(page['/Annots'],NullObject) and page['/Annots']!=[]:raise ValueError('Annotation survived')
        resources(page['/Resources'])
        contents=page.get('/Contents')
        streams=contents.get_object() if contents is not None else []
        for stream in streams if isinstance(streams,list) else [streams]:_keys(stream.get_object(),'/Length /Filter /DecodeParms')
        for values,operator in ContentStream(contents,reader).operations if contents is not None else []:
            if operator not in allowed_ops or operator in {b'Tr',b'Ts'} and (len(values)!=1 or values[0]!=0):raise ValueError('Hidden content survived')
    return tuple(payloads)


def verify(data,artifact_id,plans):
    if not data.startswith(b'%PDF-') or not data.rstrip().endswith(b'%%EOF'):raise ValueError('Invalid PDF framing')
    reader=PdfReader(BytesIO(data),strict=True)
    with pymupdf.open(stream=data,filetype='pdf') as doc:
        if doc.page_count!=len(plans) or doc.page_count!=len(reader.pages):raise ValueError('Page count changed')
        payloads=structure(reader,doc)
        for number,(page,plan) in enumerate(zip(doc,plans,strict=True),1):
            old_geometry,text_hash,rects,images=plan
            if geometry(page)!=old_geometry:raise ValueError('Page geometry changed')
            if digest((artifact_id,number,'native'),canonical(reader.pages[number-1].extract_text() or ''))!=text_hash:
                raise ValueError('Native text survived or unrelated text changed')
            current=page.get_image_info(xrefs=True)
            if len(current)!=len(images):raise ValueError('Image inventory changed')
            used=set()
            for item,(placement,image_plan) in zip(current,images,strict=True):
                if tuple(item['bbox'])!=placement or item['xref'] in used or not item['xref']:raise ValueError('Image source changed')
                used.add(item['xref'])
                with Image.open(BytesIO(doc.extract_image(item['xref'])['image'])) as image:
                    if image.size!=image_plan[1]:raise ValueError('Image dimensions changed')
                    check_pixels(image,image_plan[2])
            if used!={entry[0] for entry in page.get_images(full=True)}:raise ValueError('Hidden image resource')
            for trace in page.get_texttrace():
                if trace['type']!=0:raise ValueError('Invisible text')
            if rects:
                # Re-render the serialized page. Inspect pixel centers wholly
                # inside the coverage rectangle to exclude raster edge aliasing.
                if page.rect.width*2>4096 or page.rect.height*2>4096:raise ValueError('Verification render limit')
                pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
                with Image.frombytes('RGB',(pix.width,pix.height),pix.samples) as rendered:
                    for rect in rects:
                        box=pymupdf.Rect(rect)*page.rotation_matrix
                        pixel=(ceil(box.x0*2),ceil(box.y0*2),floor(box.x1*2),floor(box.y1*2))
                        if pixel[0]>=pixel[2] or pixel[1]>=pixel[3]:raise ValueError('Unverifiable tiny coverage')
                        check_pixels(rendered,[pixel])
        return payloads

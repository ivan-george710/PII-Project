"""Find known sensitive values in serialized PDF pixels and map source crops."""
from pathlib import Path
from tempfile import TemporaryDirectory
import re
from math import floor,ceil
import pymupdf as fitz
from PIL import Image,ImageOps
from .models import OCRTextBlock


def residual_blocks(extraction, artifact, redaction, ocr):
    normalized=lambda text:re.sub(r'[^a-z0-9]','',text.lower())
    known={normalized(record.original_text) for record in redaction.redactions
           if len(normalized(record.original_text))>=5}
    if not known:return []
    found=[]
    with fitz.open(artifact.path) as returned,fitz.open(extraction.source_path) as original,TemporaryDirectory() as directory:
        path=Path(directory)/'scan.png'
        for page in extraction.pages:
            if page.extraction_method!='ocr':continue
            dpi=extraction.pdf_source.ocr_dpi_by_page[str(page.page_number)]
            pixels=returned[page.page_number-1].get_pixmap(dpi=dpi,colorspace=fitz.csRGB,alpha=False,annots=False)
            pixels.save(path)
            blocks=ocr.extract_image(path)
            leaking=[block for block in blocks if any(value in normalized(re.sub(r'\[[^\]]+\]', '', block.text)) for value in known)]
            if not leaking:continue
            source=original[page.page_number-1].get_pixmap(dpi=dpi,colorspace=fitz.csRGB,alpha=False,annots=False)
            with Image.frombytes('RGB',(source.width,source.height),source.samples) as image:
                for block in leaking:
                    points=block.bounding_box
                    box=(max(0,floor(min(p[0] for p in points))-2),max(0,floor(min(p[1] for p in points))-2),
                         min(source.width,ceil(max(p[0] for p in points))+2),min(source.height,ceil(max(p[1] for p in points))+2))
                    with image.crop(box) as crop:
                        enlarged=crop.resize((crop.width*3,crop.height*3))
                        padded=ImageOps.expand(enlarged,border=(32,max(40,enlarged.width//16),32,max(40,enlarged.width//16)),fill='white')
                        padded.save(path);padded.close();enlarged.close()
                    actual=ocr.extract_image(path)
                    text=' '.join(b.text for b in actual)
                    if not text.strip():
                        with image.crop(box) as crop:crop.save(path)
                        text=ocr.extract_line(path)
                    if not text.strip():
                        # Reuse already fingerprinted original OCR evidence when
                        # tightly cropped text cannot be independently decoded.
                        area=fitz.Rect(box)
                        overlap=[b.text for b in page.blocks if not b.mask_only and
                            (fitz.Rect(min(p[0] for p in b.bounding_box),min(p[1] for p in b.bounding_box),
                                       max(p[0] for p in b.bounding_box),max(p[1] for p in b.bounding_box)) & area).get_area()>0]
                        text=' '.join(overlap)
                    if not text.strip():
                        raise ValueError('Residual region lacks original OCR evidence')
                    x0,y0,x1,y1=box
                    found.append((page.page_number,OCRTextBlock(text,1.0,
                        [[x0,y0],[x1,y0],[x1,y1],[x0,y1]],mask_only=True)))
    return found

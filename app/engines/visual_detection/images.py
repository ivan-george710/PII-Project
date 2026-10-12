"""Bounded canonical rasters and actual irreversible pixel transformation."""
from hashlib import sha256
from io import BytesIO
from math import floor, ceil
from PIL import Image, ImageOps, ImageFilter

MAX_PIXELS=16_777_216
MAX_BYTES=25*1024*1024


def decode(data, frame='display'):
    if not isinstance(data,bytes) or len(data)>MAX_BYTES:
        raise ValueError('Unsupported image')
    with Image.open(BytesIO(data)) as original:
        if original.format not in {'PNG','JPEG'} or original.width*original.height>MAX_PIXELS or getattr(original,'n_frames',1)!=1:
            raise ValueError('Unsupported image')
        original.load()
        image=ImageOps.exif_transpose(original) if frame=='display' else original.copy()
        # Flatten alpha before inference and regeneration: invisible RGB and
        # original alpha-mask detail must not preserve an alternate face payload.
        rgba=image.convert('RGBA');fresh=Image.new('RGB',image.size,'white');fresh.paste(rgba,mask=rgba.getchannel('A'))
        image.close();rgba.close();fresh.info.clear()
        return fresh


def encode(image, extension='.png'):
    fresh=Image.frombytes('RGB',image.size,image.convert('RGB').tobytes())
    stream=BytesIO()
    if extension.lower() in {'.jpg','.jpeg'}:fresh.save(stream,format='JPEG',quality=95,subsampling=0)
    else:fresh.save(stream,format='PNG')
    fresh.close()
    return stream.getvalue()


def pixel_hash(image):return sha256(image.convert('RGB').tobytes()).hexdigest()


def pixel_box(box,width,height):
    x,y,w,h=box
    if not 0<=x<x+w<=1.000001 or not 0<=y<y+h<=1.000001:raise ValueError('Invalid face region')
    return max(0,floor(x*width)),max(0,floor(y*height)),min(width,ceil((x+w)*width)),min(height,ceil((y+h)*height))


def blur(image, faces):
    result=Image.frombytes('RGB',image.size,image.convert('RGB').tobytes())
    evidence=[]
    for face in sorted(faces,key=lambda f:f.detection_id):
        box=pixel_box(face.bounding_box,*result.size)
        region=result.crop(box)
        radius=max(12, max(region.size)*.22)
        # Heavy downsampling discards facial spatial detail before Gaussian blur;
        # rebuilding ensures actual pixels, not a reversible overlay/CSS effect.
        coarse=region.resize((max(1,region.width//24),max(1,region.height//24)),Image.Resampling.BOX)
        enlarged=coarse.resize(region.size,Image.Resampling.BILINEAR)
        transformed=enlarged.filter(ImageFilter.GaussianBlur(radius))
        before=pixel_hash(region)
        if pixel_hash(transformed)==before:raise ValueError('Face transformation changed no pixels')
        result.paste(transformed,box)
        evidence.append(dict(detection_id=face.detection_id,box=list(box),radius=radius,source_region_sha256=before))
        region.close();coarse.close();enlarged.close();transformed.close()
    for item in evidence:
        item['transformed_region_sha256']=pixel_hash(result.crop(tuple(item['box'])))
    return result,evidence

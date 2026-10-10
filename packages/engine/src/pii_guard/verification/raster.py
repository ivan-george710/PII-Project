"""Decode serialized pixels and inspect coverage independently of painting."""
from io import BytesIO
from math import floor, ceil

from PIL import Image

from pii_guard.redaction.metadata import verify_encoded_image_metadata
from .evidence import digest


def pixel_rect(box, width, height):
    x, y, w, h = box
    if w <= 0 or h <= 0 or x < -1e-9 or y < -1e-9 or x+w > 1+1e-9 or y+h > 1+1e-9:
        raise ValueError('Invalid image region')
    return (max(0, floor(x*width)), max(0, floor(y*height)),
            min(width, ceil((x+w)*width)), min(height, ceil((y+h)*height)))


def oriented_rect(rect, size, orientation):
    l, t, r, b = rect
    w, h = size
    transforms = {1:(l,t,r,b), 2:(w-r,t,w-l,b), 3:(w-r,h-b,w-l,h-t),
        4:(l,h-b,r,h-t), 5:(t,l,b,r), 6:(h-b,l,h-t,r),
        7:(h-b,w-r,h-t,w-l), 8:(t,w-r,b,w-l)}
    return transforms[orientation]


def image_evidence(data, key, boxes=(), *, orient=False):
    with Image.open(BytesIO(data)) as image:
        if image.format not in {'PNG','JPEG'} or getattr(image, 'n_frames', 1) != 1 or image.width*image.height > 16777216:
            raise ValueError('Unsupported source image')
        image.load()
        orientation = image.getexif().get(274, 1)
        if orientation not in range(1,9) or not orient and orientation != 1:
            raise ValueError('Unsupported source orientation')
        size = image.size
        regions = tuple(pixel_rect(box,*size) for box in boxes)
        fingerprints = tuple(digest((key,rect),image.crop(rect).convert('RGBA').tobytes()) for rect in regions)
        if orient:
            regions = tuple(oriented_rect(rect,size,orientation) for rect in regions)
            if orientation >= 5:
                size = size[::-1]
        return (key,size,regions,fingerprints)


def check_pixels(image, regions, *, lossy=False):
    image.load()
    rgba = image.convert('RGBA')
    try:
        for rect in regions:
            l,t,r,b = rect
            if not 0 <= l < r <= image.width or not 0 <= t < b <= image.height:
                raise ValueError('Impossible pixel region')
            with rgba.crop(rect) as crop:
                limits = crop.getextrema()
            # JPEG quality-95 recompression introduces edge ringing. No alpha
            # transparency is allowed and every RGB channel remains near black.
            maximum = 64 if lossy else 0
            if any(channel[1] > maximum for channel in limits[:3]) or limits[3] != (255,255):
                raise ValueError('Non-opaque or surviving source pixels')
            if lossy:
                # Fully covered JPEG 8x8 DCT blocks have no boundary ringing.
                # Require exact black there: a dark but readable payload must
                # not pass merely because its extrema are below the edge bound.
                interior=(ceil(l/8)*8,ceil(t/8)*8,floor(r/8)*8,floor(b/8)*8)
                if interior[0]>=interior[2] or interior[1]>=interior[3]:
                    raise ValueError('JPEG region too small to verify independently')
                with rgba.crop(interior) as stable:
                    if stable.getextrema()!=((0,0),(0,0),(0,0),(255,255)):
                        raise ValueError('Nonuniform JPEG redaction interior')
    finally:
        rgba.close()


def verify_image(data, plan, *, output_format=None):
    _, size, regions, _ = plan
    with Image.open(BytesIO(data)) as image:
        if image.format not in {'PNG','JPEG'} or output_format and image.format != output_format:
            raise ValueError('Unexpected image type')
        if image.size != size or getattr(image,'n_frames',1) != 1:
            raise ValueError('Unexpected image dimensions')
        verify_encoded_image_metadata(data,image.format)  # Shared format policy only.
        check_pixels(image,regions,lossy=image.format=='JPEG')
        if 'A' in image.getbands():
            with image.convert('RGBA') as rgba:
                if any(a==0 and (r or g or b) for r,g,b,a in rgba.getdata()):
                    raise ValueError('Invisible RGB payload')

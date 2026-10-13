from dataclasses import dataclass, field
from math import isfinite
import re

VISUAL_ISSUES=frozenset({'external_visual_media','missing_visual_media','unmapped_visual_placement',
    'embedded_visual_objects','charts_or_vector_content','uninspected_visual_constructs','unsupported_image_format',
    'oversized_image','image_decode_failed','unmapped_pdf_raster','unmapped_pdf_image','uninspected_pdf_vector_content',
    'uninspected_pdf_annotations','uninspected_image_parts','uninspected_pdf_image_resources'})


@dataclass
class VisualUnit:
    unit_id: str
    kind: str
    source_ref: str
    image_sha256: str
    pixel_sha256: str
    width: int
    height: int
    frame: str
    locations: list[int]
    placements: list[dict] = field(default_factory=list)
    mapped: bool = True


@dataclass
class FaceDetection:
    detection_id: str
    unit_id: str
    bounding_box: list[float]  # padded normalized x,y,width,height in unit frame
    confidence: float
    document_format: str
    page_number: int
    locations: list[int]
    source_ref: str
    entity_type: str = 'FACE'
    category: str = 'BIOMETRIC'
    recognizer: str = 'YuNet'
    detection_method: str = 'local_cpu_visual'
    final_decision: str = 'CONFIRM'
    validation_decision: str = 'CONFIRM'
    validation_reason: str = 'mapped_face_privacy_policy'


@dataclass
class VisualInspection:
    source_sha256: str
    units: list[VisualUnit] = field(default_factory=list)
    faces: list[FaceDetection] = field(default_factory=list)
    unsupported: dict[str, int] = field(default_factory=dict)
    policy_version: str = 'face-1.0'
    detector_threshold: float = .35
    confirm_threshold: float = .85
    detection_seconds: float = 0.0
    cache_hits: int = 0

    def validate(self):
        if not re.fullmatch(r'[0-9a-f]{64}',self.source_sha256):raise ValueError('Invalid visual source hash')
        if len({u.unit_id for u in self.units})!=len(self.units) or len({f.detection_id for f in self.faces})!=len(self.faces):
            raise ValueError('Duplicate visual identifiers')
        units={u.unit_id:u for u in self.units}
        for u in self.units:
            if (u.kind not in {'office_media','pdf_raster','pdf_image','standalone_image'} or type(u.width) is not int or type(u.height) is not int
                or u.width<=0 or u.height<=0 or not 0<u.width*u.height<=16_777_216 or not re.fullmatch(r'I\d{6,}',u.unit_id)
                or type(u.mapped) is not bool or u.frame not in {'raw','display'}
                or not re.fullmatch(r'[0-9a-f]{64}',u.image_sha256) or not re.fullmatch(r'[0-9a-f]{64}',u.pixel_sha256)):
                raise ValueError('Invalid visual source')
            if not u.locations or any(type(n) is not int or n<1 for n in u.locations):
                raise ValueError('Invalid visual location')
        for f in self.faces:
            x,y,w,h=f.bounding_box
            if (f.unit_id not in units or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not isfinite(v) for v in f.bounding_box)
                or not (0<=x<1 and 0<=y<1 and 0<w<=1 and 0<h<=1 and x+w<=1.000001 and y+h<=1.000001)
                or not isfinite(f.confidence) or not 0<=f.confidence<=1 or f.final_decision not in {'CONFIRM','REJECT','REVIEW'}
                or isinstance(f.confidence,bool) or not re.fullmatch(r'V\d{6,}',f.detection_id)
                or f.entity_type!='FACE' or f.category!='BIOMETRIC' or f.recognizer!='YuNet'
                or f.locations!=units[f.unit_id].locations or f.page_number!=f.locations[0] or f.source_ref!=units[f.unit_id].source_ref):
                raise ValueError('Invalid mapped face')
        if set(self.unsupported)-VISUAL_ISSUES or any(type(v) is not int or v<0 for v in self.unsupported.values()):
            raise ValueError('Invalid visual inventory')
        return self

    def summary(self):
        self.validate()
        return dict(inspected_visual_units=len(self.units),detected_faces=len(self.faces),
                    confirmed_faces=sum(f.final_decision=='CONFIRM' for f in self.faces),
                    review_faces=sum(f.final_decision=='REVIEW' for f in self.faces),
                    rejected_faces=sum(f.final_decision=='REJECT' for f in self.faces),
                    face_placements=sum(len(next(u for u in self.units if u.unit_id==f.unit_id).placements) for f in self.faces),
                    unsupported_visual_units=sum(self.unsupported.values()),unsupported=dict(self.unsupported),
                    detection_seconds=self.detection_seconds,cache_hits=self.cache_hits,policy_version=self.policy_version,
                    coverage_verified=False)


def restore_visual(data):
    if data is None:return None
    return VisualInspection(**{**data,'units':[VisualUnit(**u) for u in data['units']],
                              'faces':[FaceDetection(**f) for f in data['faces']]}).validate()

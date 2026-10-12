"""Visual rows participate in Engine 5's existing replay/revision contract."""
from dataclasses import dataclass
from copy import deepcopy
from .models import FaceDetection


@dataclass
class VisualAuditRecord:
    detection_id: str
    document_id: str
    original_detection: FaceDetection
    effective_detection: FaceDetection
    automated_decision: str
    effective_decision: str
    redaction_status: str
    corrected: bool = False


def initial_visual_rows(extraction):
    if extraction.visual is None:return []
    extraction.visual.validate()
    return [dict(id=f.detection_id,original=deepcopy(f),automated=f.final_decision,effective=deepcopy(f),
                 decision=f.final_decision,corrected=False,visual=True,order=n)
            for n,f in enumerate(extraction.visual.faces)]

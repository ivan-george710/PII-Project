"""Prepare evidence before rewriting; independently verify the file read back.

No files are published or deleted here. A future staging owner must remove a
failed artifact and publish only after verifying every artifact in the submission.
"""
from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path
import stat
from uuid import UUID

from pii_guard.models import ExtractedTextBlock, SourceLocation
from pii_guard.rules.policy import RedactionTarget
from .evidence import context, state_of, identity, digest, failure
from .raster import image_evidence, verify_image


MIMES={'image/png':'png','image/jpeg':'jpeg','application/pdf':'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'docx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation':'pptx'}


def prepare_verification(original: bytes, *, artifact_id: UUID, mime_type: str,
                         targets: Iterable[RedactionTarget]=(),
                         blocks: Iterable[ExtractedTextBlock]=(),
                         sources: Iterable[SourceLocation]=(), output_mime: str|None=None,
                         verification_markers: Iterable[str|bytes]=()):
    """Trusted internal context. Fingerprints/evidence are excluded from dumps.

    Optional markers are for known fixture leaks, not a substitute for detection.
    Only marker lengths and SHA-256 hashes survive preparation.
    """
    try:
        if not isinstance(artifact_id,UUID) or mime_type not in MIMES or not isinstance(original,bytes) or not 0<len(original)<=25*1024*1024:
            raise ValueError('Invalid original artifact')
        kind=MIMES[mime_type];output_mime=output_mime or mime_type
        if output_mime not in MIMES or (kind not in {'png','jpeg'} and output_mime!=mime_type) or kind in {'png','jpeg'} and MIMES[output_mime] not in {'png','jpeg'}:
            raise ValueError('Invalid format transition')
        known,source_map={},{}
        for block in blocks:
            if not isinstance(block,ExtractedTextBlock):raise ValueError('Invalid original block')
            block=ExtractedTextBlock.model_validate(block.model_dump())
            loc=block.location
            if loc.artifact_id!=artifact_id or loc.source_ref in known or len(block.text)>1000000:
                raise ValueError('Wrong or excessive original block')
            known[loc.source_ref]=block;source_map[identity(loc)]=loc
        for source in sources:
            if not isinstance(source,SourceLocation):raise ValueError('Invalid original source')
            loc=SourceLocation.model_validate(source.model_dump())
            if loc.artifact_id!=artifact_id or loc.kind not in {'ocr','face'} or loc.bbox is None:
                raise ValueError('Wrong original region')
            key=identity(loc)
            if key in source_map and source_map[key]!=loc:raise ValueError('Conflicting original source')
            source_map[key]=loc
        accepted=[]
        for target in targets:
            if not isinstance(target,RedactionTarget):raise ValueError('Only enabled targets accepted')
            checked=RedactionTarget.model_validate(target.model_dump());loc=checked.location
            source=source_map.get(identity(loc))
            if source is None or loc.artifact_id!=artifact_id:raise ValueError('Missing original source')
            if loc.kind!='face' and not 0<=loc.start<loc.end<=source.end:raise ValueError('Invalid original span')
            if loc.kind=='native_text' and loc.source_ref not in known:raise ValueError('Missing original text')
            accepted.append(checked)
            if len(accepted)>10000:raise ValueError('Excessive targets')
        # Caller mutations after preparation cannot change any captured evidence.
        if kind in {'png','jpeg'}:
            expected_signature=b'\x89PNG\r\n\x1a\n' if kind=='png' else b'\xff\xd8'
            if not original.startswith(expected_signature):raise ValueError('Wrong original type')
            for loc in source_map.values():
                ref=loc.source_ref or ''
                valid=ref=='image' if loc.kind=='face' else ref.startswith('image:ocr:') and ref[10:].isascii() and ref[10:].isdigit()
                if not valid or loc.page_number is not None or loc.slide_number is not None or loc.kind=='ocr' and loc.start!=0:
                    raise ValueError('Wrong image source')
            plan=image_evidence(original,(artifact_id,'image'),(t.location.bbox for t in accepted),orient=True)
        elif kind in {'docx','pptx'}:
            from pii_guard.redaction.office import unpack
            from pii_guard.redaction.metadata import sanitize_office_metadata
            from . import office
            if any(t.location.kind != 'face' and t.location.source_ref not in known for t in accepted):raise ValueError('Missing Office block')
            parts=unpack(original);sanitize_office_metadata(parts,kind)
            plan=office.prepare(parts,kind,artifact_id,known,accepted,tuple(loc for loc in source_map.values() if loc.kind == "face"))
        else:
            from . import pdf
            if not original.startswith(b'%PDF-') or not original.rstrip().endswith(b'%%EOF'):
                raise ValueError('Wrong original PDF type or framing')
            if any(loc.kind=='ocr' and loc.source_ref not in known for loc in source_map.values()):
                raise ValueError('PDF OCR requires original blocks')
            for loc in source_map.values():
                if loc.kind=='face' and (not loc.page_number or loc.slide_number is not None or loc.source_ref!=f'pdf:page:{loc.page_number}:rendered'):
                    raise ValueError('Invalid PDF face source')
            plan=pdf.prepare(original,artifact_id,known,accepted)
            if any(loc.page_number is None or loc.page_number>len(plan) for loc in source_map.values()):
                raise ValueError('Impossible original page')
        markers=[]
        for value in verification_markers:
            data=value.encode() if isinstance(value,str) else value
            if not isinstance(data,bytes) or not 4<=len(data)<=512 or len(markers)>=16:raise ValueError('Invalid fixture marker')
            markers.append((len(data),sha256(data).digest()))
        text_fingerprints=tuple((identity(t.location),t.location.start,t.location.end,
            digest((identity(t.location),t.location.start,t.location.end),known[t.location.source_ref].text[t.location.start:t.location.end]))
            for t in accepted if t.location.kind=='native_text')
        return context({'kind':kind,'artifact_id':artifact_id,'mime':output_mime,
            'original_sha256':sha256(original).hexdigest(),'plan':plan,
            'text_fingerprints':text_fingerprints,'markers':tuple(markers)})
    except Exception:
        raise failure(artifact_id if isinstance(artifact_id,UUID) else None) from None


def _markers_absent(payloads,markers):
    # Deterministic bounded scan; never retain or reveal a matched marker.
    work=0
    for data in payloads:
        for length,fingerprint in markers:
            windows=max(0,len(data)-length+1);work+=windows
            if work>2000000:raise ValueError('Fixture verification scan exceeds bound')
            if any(sha256(data[index:index+length]).digest()==fingerprint for index in range(windows)):
                raise ValueError('Known fixture leak survived')


def verify_artifact(output_path: Path, evidence, *, artifact_id: UUID, mime_type: str,
                    submission_id: UUID|None=None, original_path: Path|None=None) -> None:
    """Read/reopen the actual output. Failure leaves deletion to its staging owner.

    Success is valid for these bytes only: the future publisher must prevent
    mutation/replacement between verification and publication (or recheck a hash).
    """
    try:
        state=state_of(evidence)
        if state.get('artifact_id')!=artifact_id or not isinstance(artifact_id,UUID) or state.get('mime')!=mime_type:
            raise ValueError('Wrong artifact evidence or MIME')
        if original_path is not None:
            original_path=Path(original_path)
            original_stat=original_path.lstat()
            if not stat.S_ISREG(original_stat.st_mode) or not 0<original_stat.st_size<=25*1024*1024:
                raise ValueError('Invalid original source file')
            with original_path.open('rb') as stream:
                original=stream.read(25*1024*1024+1)
            if sha256(original).hexdigest()!=state['original_sha256']:
                raise ValueError('Original source changed after evidence capture')
        path=Path(output_path)
        before=path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=100*1024*1024:raise ValueError('Invalid output file')
        with path.open('rb') as stream:
            import os
            opened=os.fstat(stream.fileno())
            if (opened.st_dev,opened.st_ino,opened.st_size)!=(before.st_dev,before.st_ino,before.st_size):raise ValueError('Output changed')
            data=stream.read(100*1024*1024+1)
            after=os.fstat(stream.fileno())
        if len(data)!=before.st_size or (after.st_size,after.st_mtime_ns)!=(opened.st_size,opened.st_mtime_ns):raise ValueError('Output changed during verification')
        kind=state['kind'];plan=state['plan']
        if kind in {'png','jpeg'}:
            verify_image(data,plan,output_format='PNG' if mime_type=='image/png' else 'JPEG')
            payloads=(data,)
        elif kind in {'docx','pptx'}:
            from . import office
            payloads=office.verify(data,kind,artifact_id,plan)
        elif kind=='pdf':
            from . import pdf
            payloads=(data,*pdf.verify(data,artifact_id,plan))
        else:raise ValueError('Wrong evidence kind')
        _markers_absent(payloads,state['markers'])
    except Exception:
        raise failure(artifact_id if isinstance(artifact_id,UUID) else None,
            submission_id if isinstance(submission_id,UUID) else None) from None

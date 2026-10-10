"""Private source-bound evidence. Dumps/repr contain neither hashes nor PII."""
from __future__ import annotations

from hashlib import sha256
import json
from types import MappingProxyType

from pydantic import PrivateAttr

from pii_guard.errors import ProcessingError, ProcessingErrorCode
from pii_guard.models import EngineBaseModel, SourceLocation
from pii_guard.rules.policy import RedactionTarget


class VerificationContext(EngineBaseModel):
    # No public fields. Construct only through the preparation APIs, before writing.
    _state: object = PrivateAttr(default=None)


def failure(artifact_id=None, submission_id=None):
    return ProcessingError(ProcessingErrorCode.REDACTION_FAILED,
        'Output verification failed: invalid evidence, structure or redaction.',
        artifact_id=artifact_id, submission_id=submission_id)


def identity(location):
    return (location.artifact_id, location.kind, location.page_number,
            location.slide_number, location.source_ref, location.bbox)


def digest(source, value):
    """Length-delimited source identity and value prevent cross-unit comparisons."""
    key = json.dumps(source, default=str, ensure_ascii=True, separators=(',', ':')).encode()
    data = value.encode('utf-8') if isinstance(value, str) else value
    return sha256(len(key).to_bytes(8, 'big') + key + data).hexdigest()


def expected_text(text, spans, replacement='[REDACTED]'):
    # Independent interval sweep; does not call the text writer/merge helper.
    events = {0:0,len(text):0}
    for lo, hi in spans:
        if type(lo) is not int or type(hi) is not int or not 0 <= lo < hi <= len(text):
            raise ValueError('Invalid text span')
        events[lo]=events.get(lo,0)+1
        events[hi]=events.get(hi,0)-1
    result, active, cursor = [], 0, 0
    for boundary in sorted(events):
        if not active:result.append(text[cursor:boundary])
        updated=active+events[boundary]
        if not active and updated:result.append(replacement)
        active=updated;cursor=boundary
    return ''.join(result)


def context(state):
    result = VerificationContext()
    result._state = MappingProxyType(state)
    return result


def state_of(value):
    if not isinstance(value, VerificationContext) or not isinstance(value._state, MappingProxyType):
        raise ValueError('Evidence must be prepared internally')
    return value._state


def prepare_text_verification(original, targets=(), *, source=None):
    """Capture a whole-unit expected digest without retaining original text."""
    try:
        if not isinstance(original, str) or len(original) > 100000:
            raise ValueError('Invalid original text')
        if not original and source is None:
            if any(True for _ in targets):raise ValueError('Empty text cannot have targets')
            key=(None,'message',None,None,None,None)
            return context({'kind':'text','identity':key,'source_span':(0,0),
                'original':digest(key,''),'expected':digest(key,''),'targets':()})
        loc = SourceLocation(artifact_id=None,kind='message',page_number=None,slide_number=None,
            source_ref=None,start=0,end=len(original),bbox=None) if source is None else SourceLocation.model_validate(source.model_dump())
        if loc.kind not in {'message', 'native_text', 'ocr'} or loc.start != 0 or loc.end != len(original):
            raise ValueError('Invalid original source')
        if loc.kind == 'message' and identity(loc) != (None, 'message', None, None, None, None):
            raise ValueError('Invalid message identity')
        if loc.kind != 'message' and (loc.artifact_id is None or not loc.source_ref):
            raise ValueError('Missing artifact identity')
        spans = []
        for target in targets:
            if not isinstance(target, RedactionTarget):
                raise ValueError('Expected enabled target')
            checked = RedactionTarget.model_validate(target.model_dump())
            if identity(checked.location) != identity(loc):
                raise ValueError('Wrong source')
            spans.append((checked.location.start, checked.location.end))
            if len(spans) > 10000:
                raise ValueError('Excessive targets')
        key = identity(loc)
        return context({'kind': 'text', 'identity': key,
            'source_span':(loc.start,loc.end),
            'original': digest(key, original),
            'expected': digest(key, expected_text(original, spans)),
            'targets': tuple((lo, hi, digest((key,lo,hi), original[lo:hi])) for lo, hi in spans)})
    except Exception:
        raise failure() from None


def verify_text(sanitized, evidence, *, source=None):
    """No success payload. Artifact units require their ORIGINAL source identity."""
    try:
        state = state_of(evidence)
        key = identity(SourceLocation.model_validate(source.model_dump())) if source is not None else (None, 'message', None, None, None, None)
        if state['kind'] != 'text' or state['identity'] != key or not isinstance(sanitized, str):
            raise ValueError('Wrong verification unit')
        if source is not None and (source.start,source.end)!=state['source_span']:
            raise ValueError('Wrong original source span')
        if digest(key, sanitized) != state['expected']:
            raise ValueError('Unexpected sanitized text')
    except Exception:
        raise failure() from None

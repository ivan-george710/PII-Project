"""Complete, staged privacy pipeline. No artifact escapes before all verify."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from pii_guard.models import SanitizeRequest, SanitizeResult, SanitizedArtifact
from pii_guard.detection.text import TextDetector
from pii_guard.detection.faces import FaceDetector
from pii_guard.ocr.engine import RapidOCREngine
from pii_guard.rules.policy import PolicyEvaluator
from pii_guard.redaction.text import redact_text, redact_block
from pii_guard.verification.artifact import prepare_verification, verify_artifact
from pii_guard.errors import ProcessingError, ProcessingErrorCode


class PrivacyEngine:
    def __init__(self, *, text_detector=None, ocr_provider=None, face_detector=None):
        self.text_detector = text_detector or TextDetector()
        self.ocr_provider = ocr_provider or RapidOCREngine()
        self.face_detector = face_detector or FaceDetector()

    def sanitize(self, request: SanitizeRequest) -> SanitizeResult:
        from pii_guard.inspection.file_type import detect_file_type
        from pii_guard.extraction import (
            extract_image,
            extract_pdf,
            extract_docx,
            extract_pptx,
        )
        from pii_guard.extraction.pdf import _render_page
        from pii_guard.verification.office import inventory
        from pii_guard.redaction.office import unpack
        from pii_guard.redaction.image import redact_image
        from pii_guard.redaction.pdf import redact_pdf
        from pii_guard.redaction.docx import redact_docx
        from pii_guard.redaction.pptx import redact_pptx
        from pypdf import PdfReader

        request = SanitizeRequest.model_validate(request.model_dump())
        all_blocks = []
        all_faces = []
        inputs = []
        for artifact in request.artifacts:
            detected = detect_file_type(artifact.source_path, artifact_id=artifact.id)
            kind = detected.file_format
            raw = artifact.source_path.read_bytes()
            if artifact.declared_mime and artifact.declared_mime != detected.mime_type:
                raise ProcessingError(
                    ProcessingErrorCode.UNSUPPORTED_FILE,
                    "Declared file type does not match content.",
                    artifact_id=artifact.id,
                )
            extract = {
                "png": extract_image,
                "jpeg": extract_image,
                "pdf": extract_pdf,
                "docx": extract_docx,
                "pptx": extract_pptx,
            }[kind]
            extracted = extract(
                artifact.source_path,
                artifact_id=artifact.id,
                filename=artifact.filename,
                ocr_provider=self.ocr_provider,
            )
            faces = []
            if kind in {"png", "jpeg"}:
                faces = self.face_detector.detect(
                    raw, artifact_id=artifact.id, source_ref="image"
                )
            elif kind == "pdf":
                for number in range(1, len(PdfReader(BytesIO(raw)).pages) + 1):
                    rendered = _render_page(
                        artifact.source_path, number, artifact.id, 4096
                    )
                    faces.extend(
                        self.face_detector.detect(
                            rendered.data,
                            artifact_id=artifact.id,
                            source_ref=rendered.source_ref,
                            page_number=number,
                        )
                    )
            else:
                parts = unpack(raw)
                _, images, _, _ = inventory(parts, kind)
                for ref, (media, slide, placement) in images.items():
                    faces.extend(
                        self.face_detector.detect(
                            parts[media],
                            artifact_id=artifact.id,
                            source_ref=ref,
                            slide_number=slide,
                            placement=placement,
                        )
                    )
            inputs.append((artifact, extracted, raw, faces))
            all_blocks.extend(extracted.blocks)
            all_faces.extend(faces)
        detected = self.text_detector.detect(text=request.text, blocks=all_blocks)
        evaluation = PolicyEvaluator(
            request.policy, submission_id=request.submission_id
        ).evaluate(
            (*detected.accepted, *all_faces), text=request.text, blocks=all_blocks
        )
        targets = evaluation.redaction_targets
        safe_text = redact_text(
            request.text, [t for t in targets if t.location.kind == "message"]
        )
        output_dir = request.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        published = []
        try:
            with TemporaryDirectory(prefix=".pii-stage-", dir=output_dir) as staging:
                planned = []
                for artifact, extracted, raw, faces in inputs:
                    local = [
                        t for t in targets if t.location.artifact_id == artifact.id
                    ]
                    sources = [f.location for f in faces]
                    evidence = prepare_verification(
                        raw,
                        artifact_id=artifact.id,
                        mime_type=extracted.mime_type,
                        targets=local,
                        blocks=extracted.blocks,
                        sources=sources,
                    )
                    if extracted.file_type in {"png", "jpeg"}:
                        safe = redact_image(
                            raw,
                            local,
                            artifact_id=artifact.id,
                            sources=[b.location for b in extracted.blocks] + sources,
                        ).data
                    else:
                        renderer = {
                            "pdf": redact_pdf,
                            "docx": redact_docx,
                            "pptx": redact_pptx,
                        }[extracted.file_type]
                        safe = renderer(
                            raw,
                            local,
                            artifact_id=artifact.id,
                            blocks=extracted.blocks,
                            region_sources=sources,
                        )
                    path = Path(staging) / str(artifact.id)
                    path.write_bytes(safe)
                    path.chmod(0o600)
                    verify_artifact(
                        path,
                        evidence,
                        artifact_id=artifact.id,
                        mime_type=extracted.mime_type,
                        original_path=artifact.source_path,
                        submission_id=request.submission_id,
                    )
                    planned.append((path, artifact, extracted, safe))
                for path, artifact, extracted, safe in planned:
                    dest = (
                        output_dir
                        / f"{request.submission_id}-{artifact.id}{Path(artifact.filename).suffix.lower()}"
                    )
                    # Exclusive publication prevents replacement of another run's output.
                    with dest.open("xb") as stream:
                        stream.write(safe)
                    published.append(dest)
                    dest.chmod(0o600)
                    path.unlink()
                artifacts = [
                    SanitizedArtifact(
                        artifact_id=a.id,
                        filename=a.filename,
                        mime_type=e.mime_type,
                        output_path=dest,
                        size_bytes=len(safe),
                        sha256=sha256(safe).hexdigest(),
                        format_changed=False,
                    )
                    for dest, (_, a, e, safe) in zip(published, planned, strict=True)
                ]
            result = SanitizeResult(
                submission_id=request.submission_id,
                policy_version=request.policy.version,
                sanitized_text=safe_text,
                artifacts=artifacts,
                findings=list(evaluation.findings),
                warnings=[],
            )
            result._artifact_texts = {
                a.id: "\n\n".join(
                    redact_block(
                        block,
                        [
                            t
                            for t in targets
                            if t.location.artifact_id == a.id
                            and t.location.kind != "face"
                            and t.location.source_ref == block.location.source_ref
                        ],
                    ).sanitized_text
                    for block in e.blocks
                )
                for a, e, _, _ in inputs
            }
            return result
        except Exception:
            for path in published:
                path.unlink(missing_ok=True)
            raise ProcessingError(
                ProcessingErrorCode.REDACTION_FAILED,
                "Sanitized output could not be safely published.",
                submission_id=request.submission_id,
            ) from None

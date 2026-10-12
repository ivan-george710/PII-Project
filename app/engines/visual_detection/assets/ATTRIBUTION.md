# YuNet face detector provenance

Adapted from `ivan-george710/PII-Project`, commit
`63a416b70cf452527f42cbb1a3d9a4f80f94271f`:

- `packages/engine/src/pii_guard/detection/faces.py`
- Image/metadata reference: `packages/engine/src/pii_guard/redaction/image.py`
- Licensed asset: `packages/engine/src/pii_guard/model_assets/face_detection_yunet_2023mar.onnx`
- Model SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`

YuNet model origin: OpenCV Zoo's `face_detection_yunet_2023mar` (Shiqi Yu).
The source repository's `model_assets/index.md` pins upstream OpenCV Zoo commit
`47534e27c9851bb1128ccc0102f1145e27f23f98`, path `models/face_detection_yunet`.
The source repository's `YUNET_LICENSE.txt` (MIT, copyright 2020 Shiqi Yu)
is retained verbatim. Model bytes were copied from the source's GitHub contents
API and verified against its detector constant. No weights are downloaded at runtime.

Cadence adapts the local CPU detector algorithms; it does not import the other
repository's contracts, pipeline, policy, services, database or identity models.
The reference image redactor used black fill; Cadence implements strong pixel blur.

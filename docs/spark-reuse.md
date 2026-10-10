# Spark face-processing adaptation

Desktop/spark is a Swift/iOS app. Its Vision/CoreML APIs cannot run on the hosted Python/Linux backend. We reuse the algorithm from `Still/Services/FaceDetector.swift` and `Still/Models/FaceRegion.swift`:

- Full frame plus nine 45%-size overlapping tiles at offsets 0, .275, .55 on large images.
- Duplicate suppression at IoU > .35, or >80% containment with area ratio <2.5.
- Padding of 8% horizontally and 12% vertically, clipped to the image.

The backend uses pinned OpenCV YuNet CPU inference and also checks cardinal rotations. It masks every detected face for enabled FACE policy. It does not port expression/subject classification or reveal selected people. Opaque masks replace the original pixels; metadata/thumbnails are stripped and actual serialized output is independently verified.

Coverage includes standalone PNG/JPEG, rendered PDF pages and embedded pictures in supported DOCX/PPTX packages. Scanned text goes through real bundled RapidOCR then Presidio/custom-rule detection. Unsupported/encrypted/complex documents fail closed; legacy `.doc`/`.ppt` are not accepted. Strict Office/PDF structural support remains as documented in the engine README.

Local candid checks on Spark assets (0.35 confidence): TrainWindow 1, TrainReflection 2, SideProfile 4, LookingAway 4. These are candidate counts, not ground-truth accuracy; the latter two include additional masks. Vision's model differs, and no general detector can guarantee all faces in arbitrary images.

Model source/license and checksum: `packages/engine/src/pii_guard/model_assets/index.md`. The NASA astronaut fixture is public domain; other Spark images were tested locally, not added to this repository.

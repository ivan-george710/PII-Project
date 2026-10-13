# app/engines/visual_detection

| File | Responsibility |
|---|---|
| `__init__.py` | Public visual engine exports. |
| `audit.py` | Existing engine helper; preserve its boundary. |
| `detector.py` | Local YuNet face detection. |
| `images.py` | Canonical decoding, metadata stripping, hashes and irreversible face blur. |
| `inspection.py` | Bounded original image inventory and face detection for PDF, Office and standalone images. |
| `models.py` | Visual mappings, face findings and validated inventory. |

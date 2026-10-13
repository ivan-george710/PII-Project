# app/web

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `__init__.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `models.py` | Implemented; integration in progress | Pydantic local API boundaries, text submission and original/redacted chat response fields. |
| `server.py` | Implemented; integration in progress | Trusted-local real-engine document/text processing, samples/original previews, advisory report sync, real PDF page previews and denial-only download control. |

Subdirectories contain their own manifests when touched. Engine implementation and phase evidence remain authoritative.

| `manager_client.py` | Implemented; integration in progress | HTTPS/loopback manager transport; sends affected-only reports, caches the last loaded rules and blocks only explicit manager denial. |

`server.py` also serves bounded local Office raster-image galleries. Original files stay local; returned-image routes honor explicit manager denial. Unsupported preview formats/sizes fail explicitly.

Supported uploads now include PNG/JPEG, with real OCR/face removal and stripped PNG returns. Mixed PDF pages are OCR-processed even when they contain native text; Office embedded images have independent OCR logical segments.

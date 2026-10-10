# packages/engine/src/pii_guard/verification

Private, fail-closed output verification. Prepare original evidence before writing,
then reread staged output bytes. No publication, deletion, face detection or public
model changes belong here. Public dumps of evidence contain no hashes or content.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities. |
| `__init__.py` | Existing | Internal preparation and verification API exports. |
| `artifact.py` | Existing | Validate trusted original/target identities, capture private evidence, inspect real output files/MIME, dispatch verification, optional original-byte and fixture-marker checks; return no success payload. |
| `evidence.py` | Existing | Private Pydantic evidence, source-bound SHA-256 fingerprints, independent text expectation/verification and safe errors. |
| `raster.py` | Existing | Capture original image-region evidence, independently map orientation/pixel bounds and decode opaque coverage; validate dimensions and metadata state. |
| `office.py` | Existing | Separate serialized paragraph/placement inventory, native source fingerprints, relationship/ancillary checks, metadata absence, shared-media coverage and Office reopening. |
| `pdf.py` | Existing | Independent serialized object/stream policy, native page fingerprints, page geometry, rendered coverage, underlying image pixels and bounded known-leak payload enumeration. |

Shared security guards enforce the existing supported subset; verification never
calls a redactor. Staging ownership and mutation prevention remain pipeline duties.
Owner: [Issue 1](../../../../../docs/issues/01-privacy-engine.md).

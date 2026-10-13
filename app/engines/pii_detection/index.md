# PII detection

| File | Responsibility |
|---|---|
| `engine.py` | Presidio/spaCy classification, source-mapped OCR spacing, explicit introductions, repeated-value protection, crossing-span unions and bounded manager rules. |
| `recognizers.py` | Employee IDs, reserved-domain mailboxes and explicit secret/address/DOB/identifier fields supplement the NLP classifier. |
| `validation.py` | Version 1.2 PII disposition policy; uncertain findings remain reviewable and are masked by the redaction engine. |
| `models.py` | Detection candidates/results/errors. |
| `presidio.py` | Existing Presidio adapter. |
| `__init__.py` | Public detection exports. |

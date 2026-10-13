# app/engines/audit

| File | Responsibility |
|---|---|
| `__init__.py` | Public audit exports. |
| `engine.py` | Immutable audit, review/feedback replay and persistence; supports masked-but-unresolved findings. |
| `feedback_export.py` | Opt-in private review feedback exports. |
| `models.py` | Audit/reviewer data and errors. |
| `reporter.py` | Existing engine helper; preserve its boundary. |
| `storage.py` | Private audit storage/path guards. |

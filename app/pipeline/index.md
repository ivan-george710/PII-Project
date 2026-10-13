# app/pipeline

| File | Responsibility |
|---|---|
| `PipelineDesc.txt` | Existing pipeline description. |
| `__init__.py` | Public pipeline exports. |
| `models.py` | Pipeline status, failures and sanitized summaries. |
| `pipeline.py` | Stage orchestration, real detection/inspection/artifact generation and immutable feedback regeneration. |

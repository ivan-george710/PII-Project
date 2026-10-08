# apps/api/app/llm/providers

Provider-specific LLM integrations behind the shared client interface.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Provider adapter exports. |
| `openai.py` | Planned | Initial configurable OpenAI provider adapter; accept sanitized payloads only. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

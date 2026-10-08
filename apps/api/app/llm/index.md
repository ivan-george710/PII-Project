# apps/api/app/llm

LLM client interface and sanitized message/attachment submission.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | LLM package marker. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `client.py` | Planned | Provider-neutral request, streaming, and attachment interface. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

## Subdirectories

- [providers/](providers/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

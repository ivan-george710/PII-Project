# apps/web/src/styles

Simple chat-interface styles and shared visual tokens.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `globals.css` | Existing | Shared app styles plus responsive monochrome auth screens, larger heading hierarchy and an accessible circular send-arrow control, accessible feedback and reduced-motion support. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## Delivered interface update

`globals.css` provides the complete responsive light/dark design tokens, full-height shell, composer/menu/settings/auth layouts and reduced-motion behavior; desktop styles are outside mobile media queries.

# apps/web/src/components

Reusable UI elements shared across features.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `Button.tsx` | Implemented | Accessible shared button. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `Dialog.tsx` | Implemented | Shared accessible modal. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `FormField.tsx` | Implemented | Labeled input with validation messages. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `StatusMessage.tsx` | Implemented | Shared loading/error/status feedback. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## Interface and employee creation update

| Filename | Status | Responsibility |
|---|---|---|
| WorkspaceShell.tsx | Existing | Responsive sidebar, workspace header, keyboard-accessible mobile navigation and account controls. |
| ThemeToggle.tsx | Existing | Persist system/light/dark preference; update on system appearance changes. |
| LoadingIndicator.tsx | Existing | Compact lazy-loaded monochrome Strands status with reduced-motion and WebGL fallback. |
| Strands.jsx | Existing | React Bits upstream Strands canvas animation, installed through shadcn registry. |
| Strands.css | Existing | Canvas dimensions for the upstream Strands component. |
| Strands.LICENSE.txt | Existing | Upstream MIT plus Commons Clause license and attribution. |

`BrandMark.tsx` renders the approved shared SVG mark used in the workspace sidebar and sign-in/sign-up header; its geometry matches `public/favicon.svg`.

## PR 18 integration

WorkspaceShell links managers to workspace setup, rules/policy and employee reports, preserving shared theme/account controls.

# apps/web/src/features/chat

Plain chat messages, composer, attachments, streaming replies, and processing status.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `ChatComposer.tsx` | Planned | Message input, file selection, and send/cancel controls. |
| `MessageList.tsx` | Planned | Render conversation turns and streamed responses. |
| `AttachmentList.tsx` | Planned | Display attached files and processing states. |
| `useChat.ts` | Planned | Manage conversations, submissions, retries, and response streaming. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

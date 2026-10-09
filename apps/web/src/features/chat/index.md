# apps/web/src/features/chat

Plain chat messages, composer, attachments, streaming replies, and processing status.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `ChatComposer.tsx` | Implemented | Message input, file selection, and send/cancel controls. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `MessageList.tsx` | Implemented | Render conversation turns and streamed responses. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `AttachmentList.tsx` | Implemented | Display attached files and processing states. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `useChat.ts` | Implemented | Manage conversations, submissions, retries, and response streaming. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `AttachmentMenu.tsx` | Implemented | Composer-left plus menu for Upload file and Try test data. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `DemoSamplePicker.tsx` | Implemented | Simple grouped sample selector; insert drafts or attach files without sending. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `useDemoSamples.ts` | Implemented | Load the typed catalog and select message/file examples. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## Delivered interface update

AttachmentMenu closes after sample selection, supports Escape/outside dismissal, and uses a bounded popup. ChatComposer resizes text input and shows the compact Strands loading status. The UI uses text controls, no icons.

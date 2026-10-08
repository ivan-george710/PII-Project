**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Deliver employee chat with guarded uploads and LLM responses

Status: Draft — awaiting individual approval before GitHub creation.
Suggested ownership: Full-stack employee experience

Deliver the complete employee workflow: plain chat, file attachments, sanitization before submission, and LLM responses.

## Scope
- Implement the minimal chat page, composer, attachments, conversation history, and streaming responses.
- Implement authenticated chat/upload routes, conversation/message/attachment persistence, storage access, and file cleanup.
- Implement a guard service that resolves the employee’s company policy and calls the engine before sending anything to the provider.
- Add a provider abstraction and one working LLM integration, including a supported sanitized attachment representation.
- Preserve the sanitization boundary when resending history, handling retries, and loading conversations.
- Publish findings/actions through the reporting event interface.
- Show simple processing and failure states; block submission when sanitization cannot complete.
- Include API schemas, frontend/backend tests, and a deterministic development mode using supplied session/policy/engine/provider adapters.

## Acceptance criteria
- The complete chat flow is reviewable using development adapters and can connect to real configured integrations without rewriting the flow.
- An employee can send text and supported attachments and receive streaming replies.
- Captured outgoing provider payloads contain sanitized content and never original attachments or original sensitive history for enabled rules.
- Disabled-rule matches follow saved company policy and generate allowed events.
- Failure/retry states do not send unsanitized content or duplicate submissions/events.
- Users cannot access another employee’s conversations or files through direct resource requests.
- UI stays a plain LLM-style chat interface.

## Exact file ownership

Implement the following file plan. Shared directories assign individual files to their workstream; the directory indexes contain responsibilities and current/planned status. Existing prototype files remain reference material, not a second production implementation.

| File | Responsibility |
|---|---|
| `apps/api/app/db/models/conversation.py` | Employee-owned conversations (issue 2). |
| `apps/api/app/db/models/message.py` | Conversation turns and safe provider history (issue 2). |
| `apps/api/app/db/models/attachment.py` | File ownership, storage references, and processing state (issue 2). |
| `apps/api/app/llm/__init__.py` | LLM package marker. |
| `apps/api/app/llm/client.py` | Provider-neutral request, streaming, and attachment interface. |
| `apps/api/app/llm/providers/__init__.py` | Provider adapter exports. |
| `apps/api/app/llm/providers/openai.py` | Initial configurable OpenAI provider adapter; accept sanitized payloads only. |
| `apps/api/app/routes/chat.py` | Conversation, submission, and streaming endpoints (issue 2). |
| `apps/api/app/routes/uploads.py` | Authorized upload and sanitized-file access endpoints (issue 2). |
| `apps/api/app/schemas/chat.py` | Conversation, message, submission, and stream events (issue 2). |
| `apps/api/app/schemas/uploads.py` | File metadata, processing state, and authorized output responses (issue 2). |
| `apps/api/app/services/guard.py` | Apply company policy, sanitize, block failures, and publish events (issue 2). |
| `apps/api/app/services/chat.py` | Persist conversation flow, build safe history, and stream LLM results (issue 2). |
| `apps/api/app/storage/__init__.py` | Storage package marker. |
| `apps/api/app/storage/files.py` | Separate original/sanitized artifact storage and enforce authorized access. |
| `apps/api/app/storage/cleanup.py` | Apply configured file retention and cleanup. |
| `apps/api/migrations/versions/0002_conversations_messages_attachments.py` | Chat and attachment tables (issue 2); independent of company migration using scalar identity references until integrated metadata validation. |
| `apps/api/tests/test_chat.py` | Safe history, guarded provider calls, streaming, and retry behavior (issue 2). |
| `apps/api/tests/test_uploads.py` | Upload authorization, supported inputs, and output access (issue 2). |
| `apps/api/tests/test_guard.py` | Sanitized-only payloads, disabled rules, and blocked failures (issue 2). |
| `apps/web/src/features/chat/ChatComposer.tsx` | Message input, file selection, and send/cancel controls. |
| `apps/web/src/features/chat/MessageList.tsx` | Render conversation turns and streamed responses. |
| `apps/web/src/features/chat/AttachmentList.tsx` | Display attached files and processing states. |
| `apps/web/src/features/chat/useChat.ts` | Manage conversations, submissions, retries, and response streaming. |
| `apps/web/src/layouts/ChatLayout.tsx` | Minimal chat shell and conversation navigation (issue 2). |
| `apps/web/src/pages/Chat.tsx` | Plain employee conversation page (issue 2). |
| `apps/web/tests/chat.test.tsx` | Composer, attachment, streaming, retry, and error behavior (issue 2). |

## Working independently

Use the shared contract snapshots and development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.

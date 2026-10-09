import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatComposer } from "../src/features/chat/ChatComposer";
import { useChat } from "../src/features/chat/useChat";

vi.mock("../src/features/auth/useAuth", () => ({
  useAuth: () => ({ identity: { csrf_token: "test-csrf" } }),
}));

const baseProps = {
  draft: "",
  setDraft: vi.fn(),
  attachments: [],
  onRemoveAttachment: vi.fn(),
  onUpload: vi.fn(),
  onSend: vi.fn(),
  onCancel: vi.fn(),
  processing: false,
  samples: [],
  samplesLoading: false,
  samplesError: "",
  selectingSample: null,
  onSelectSample: vi.fn(),
  onRetrySamples: vi.fn(),
  error: "",
  onRetry: vi.fn(),
  retryAvailable: false,
};

describe("chat composer", () => {
  it("sends with Enter and preserves newline with Shift+Enter", async () => {
    const user = userEvent.setup();
    render(<ChatComposer {...baseProps} draft="hello" />);
    const input = screen.getByRole("textbox", { name: "Message" });
    await user.type(input, "{Shift>}{Enter}{/Shift}");
    expect(baseProps.onSend).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });
    expect(baseProps.onSend).toHaveBeenCalledOnce();
  });

  describe("chat streaming", () => {
    const conversationId = "33000000-0000-4000-8000-000000000001";
    const submissionId = "33000000-0000-4000-8000-000000000002";
    const assistantId = "33000000-0000-4000-8000-000000000003";
    const userMessageId = "33000000-0000-4000-8000-000000000004";
    const assistantMessageId = "33000000-0000-4000-8000-000000000005";

    function event(name: string, data: object) {
      return `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
    }

    function successfulStream() {
      return new Response(
        [
          event("processing", { type: "processing", submission_id: submissionId, stage: "sanitizing" }),
          event("sanitized", {
            type: "sanitized",
            submission_id: submissionId,
            user_message: {
              id: userMessageId,
              conversation_id: conversationId,
              role: "user",
              text: "[REDACTED]",
              attachment_ids: [],
              state: "completed",
              created_at: "2026-10-09T00:00:00Z",
            },
            attachments: [],
            policy_version: "v1",
          }),
          event("delta", {
            type: "delta",
            submission_id: submissionId,
            assistant_message_id: assistantId,
            sequence: 1,
            text: "Safe reply",
          }),
          event("done", {
            type: "done",
            submission_id: submissionId,
            assistant_message: {
              id: assistantMessageId,
              conversation_id: conversationId,
              role: "assistant",
              text: "Safe reply",
              attachment_ids: [],
              state: "completed",
              created_at: "2026-10-09T00:00:01Z",
            },
          }),
        ].join(""),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      );
    }

    function errorStream() {
      return new Response(
        [
          event("processing", { type: "processing", submission_id: submissionId, stage: "sanitizing" }),
          event("error", {
            type: "error",
            submission_id: submissionId,
            code: "PROCESSING_FAILED",
            message: "Safe processing failed.",
            retryable: true,
          }),
        ].join(""),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      );
    }

    function fetchMock(responses: Response[]) {
      return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/conversations") && !init?.method) {
          return new Response(
            JSON.stringify({
              items: [{
                id: conversationId,
                title: "Test chat",
                created_at: "2026-10-09T00:00:00Z",
                updated_at: "2026-10-09T00:00:00Z",
              }],
              next_cursor: null,
            }),
            { status: 200 },
          );
        }
        if (url.endsWith(`/conversations/${conversationId}/messages`) && !init?.method) {
          return new Response(JSON.stringify({ items: [], next_cursor: null }), { status: 200 });
        }
        if (url.endsWith(`/conversations/${conversationId}/messages`) && init?.method === "POST") {
          return responses.shift() ?? successfulStream();
        }
        throw new Error(`Unexpected request ${url}`);
      });
    }

    it("renders only sanitized history from fetch-streamed responses", async () => {
      const fetch = fetchMock([successfulStream()]);
      vi.stubGlobal("fetch", fetch);
      const { result } = renderHook(() => useChat());
      await waitFor(() => expect(result.current.activeConversation).toBe(conversationId));
      act(() => result.current.setDraft("Dana dana@example.test"));
      await act(async () => result.current.send());
      expect(result.current.messages.map((item) => item.text)).toContain("[REDACTED]");
      expect(result.current.messages.map((item) => item.text).join(" ")).not.toContain("dana@example.test");
      expect(result.current.messages.at(-1)?.text).toBe("Safe reply");
    });

    it("keeps failure visible and retries with the same idempotency key", async () => {
      const fetch = fetchMock([errorStream(), successfulStream()]);
      vi.stubGlobal("fetch", fetch);
      const { result } = renderHook(() => useChat());
      await waitFor(() => expect(result.current.activeConversation).toBe(conversationId));
      act(() => result.current.setDraft("Safe draft"));
      await act(async () => result.current.send());
      expect(result.current.error).toBe("Safe processing failed.");
      const submission = fetch.mock.calls.find((call) => call[1]?.method === "POST");
      expect(submission).toBeDefined();
      const firstBody = JSON.parse(String(submission?.[1]?.body));
      await act(async () => result.current.retry());
      await waitFor(() => expect(result.current.processing).toBe(false));
      const posts = fetch.mock.calls.filter((call) => call[1]?.method === "POST");
      expect(JSON.parse(String(posts[1][1]?.body)).client_request_id).toBe(firstBody.client_request_id);
      expect(result.current.error).toBe("");
      expect(result.current.messages.at(-1)?.text).toBe("Safe reply");
    });

    it("preserves Unicode deltas and rejects malformed SSE payloads", async () => {
      const fetch = fetchMock([new Response(
        [
          event("processing", { type: "processing", submission_id: submissionId, stage: "sanitizing" }),
          event("delta", {
            type: "delta",
            submission_id: submissionId,
            assistant_message_id: assistantId,
            sequence: 1,
            text: "こんにちは 🌿",
          }),
          event("done", {
            type: "done",
            submission_id: submissionId,
            assistant_message: {
              id: assistantMessageId,
              conversation_id: conversationId,
              role: "assistant",
              text: "こんにちは 🌿",
              attachment_ids: [],
              state: "completed",
              created_at: "2026-10-09T00:00:01Z",
            },
          }),
        ].join(""),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      ), new Response(
        'event: done\ndata: {"type":"done","unexpected":true}\n\n',
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      )]);
      vi.stubGlobal("fetch", fetch);
      const { result } = renderHook(() => useChat());
      await waitFor(() => expect(result.current.activeConversation).toBe(conversationId));
      act(() => result.current.setDraft("hello"));
      await act(async () => result.current.send());
      expect(result.current.messages.at(-1)?.text).toBe("こんにちは 🌿");
      act(() => result.current.setDraft("again"));
      await act(async () => result.current.send());
      expect(result.current.error).toBeTruthy();
    });
  });

  it("disables duplicate sends while processing and exposes cancel", () => {
    render(<ChatComposer {...baseProps} draft="hello" processing />);
    expect(screen.getByRole("button", { name: "Cancel" })).toBeEnabled();
    expect(screen.getByRole("textbox", { name: "Message" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Send" })).not.toBeInTheDocument();
  });

  it("shows retryable failure feedback and retries only on request", async () => {
    const user = userEvent.setup();
    render(
      <ChatComposer
        {...baseProps}
        error="Your request could not be safely processed."
        retryAvailable
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("could not be safely processed");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(baseProps.onRetry).toHaveBeenCalledOnce();
  });
});

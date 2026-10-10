import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/useAuth";
import { api, ApiError } from "../../lib/api";
import {
  attachment,
  apiError,
  conversation,
  conversationsPage,
  message,
  messagesPage,
  streamEvent,
  uploadInitResponse,
  type Attachment,
  type Conversation,
  type Message,
  type StreamEvent,
} from "../../lib/schemas";

const uuid = () => crypto.randomUUID();

export function useChat() {
  const { identity } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<string>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [draft, setDraft] = useState("");
  const [processing, setProcessing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastRequest, setLastRequest] = useState<{
    text: string;
    attachment_ids: string[];
    client_request_id: string;
  }>();
  const abortRef = useRef<AbortController | undefined>(undefined);

  const loadConversations = useCallback(async () => {
    const page = await api("/conversations", conversationsPage);
    setConversations(page.items);
    return page.items;
  }, []);

  const loadMessages = useCallback(async (id: string) => {
    const page = await api(`/conversations/${id}/messages`, messagesPage);
    setMessages(page.items);
  }, []);

  const createConversation = useCallback(async () => {
    const item = await api(
      "/conversations",
      conversation,
      { method: "POST", body: JSON.stringify({ title: "New chat" }) },
      identity?.csrf_token,
    );
    setConversations((items) => [item, ...items]);
    setActiveConversation(item.id);
    setMessages([]);
    return item.id;
  }, [identity?.csrf_token]);

  useEffect(() => {
    let alive = true;
    void loadConversations()
      .then(async (items) => {
        if (!alive) return;
        if (items.length) {
          setActiveConversation(items[0].id);
          await loadMessages(items[0].id);
        } else {
          await createConversation();
        }
      })
      .catch((cause) => alive && setError(cause instanceof Error ? cause.message : "Could not load chats"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
      abortRef.current?.abort();
    };
  }, [createConversation, loadConversations, loadMessages]);

  async function uploadFile(file: File) {
    if (!identity) throw new Error("Sign in to upload files");
    const init = await api(
      "/uploads/init",
      uploadInitResponse,
      {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          declared_mime: file.type,
          size_bytes: file.size,
        }),
      },
      identity.csrf_token,
    );
    const put = await fetch(init.upload.url, {
      method: init.upload.method,
      headers: init.upload.headers,
      body: file,
      credentials: "omit",
    });
    if (!put.ok) throw new ApiError(put.status, "File upload failed");
    const completed = await api(
      `/uploads/${init.attachment.id}/complete`,
      attachment,
      { method: "POST", body: "{}" },
      identity.csrf_token,
    );
    setAttachments((items) => [...items.filter((item) => item.id !== completed.id), completed]);
  }

  function removeAttachment(id: string) {
    setAttachments((items) => items.filter((item) => item.id !== id));
  }

  function addAttachment(item: Attachment) {
    setAttachments((items) =>
      items.some((existing) => existing.id === item.id) ? items : [...items, item],
    );
  }

  async function uploadFileWithStatus(file: File) {
    try {
      await uploadFile(file);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "File upload failed");
    }
  }

  async function consumeStream(
    response: Response,
    request: { text: string; attachment_ids: string[]; client_request_id: string },
    conversationId: string,
  ) {
    if (!response.ok) {
      const error = apiError.safeParse(await response.json().catch(() => null));
      throw new ApiError(
        response.status,
        error.success ? error.data.error.message : "Could not send message",
      );
    }
    if (!response.body) throw new Error("Streaming response is unavailable");
    const decoder = new TextDecoder("utf-8", { fatal: true });
    const reader = response.body.getReader();
    let buffer = "";
    let assistantText = "";
    let assistantId = "";
    let completed = false;
    setMessages((items) => [
      ...items,
      ...(request.text.trim()
        ? [{
            id: uuid(),
            conversation_id: conversationId,
            role: "user" as const,
            text: "",
            attachment_ids: request.attachment_ids,
            state: "processing" as const,
            created_at: new Date().toISOString(),
          }]
        : []),
    ]);
    const handleFrame = (frame: string) => {
      let eventName = "";
      let data = "";
      for (const line of frame.split(/\r?\n/)) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!eventName || !data) throw new Error("Invalid streaming event");
      const parsed = streamEvent.parse(JSON.parse(data)) as StreamEvent;
      if (parsed.type !== eventName) throw new Error("Mismatched streaming event");
      if (parsed.type === "sanitized") {
        setMessages((items) => [...items.filter((item) => item.state !== "processing"), parsed.user_message]);
        setAttachments(parsed.attachments);
      } else if (parsed.type === "delta") {
        assistantId = parsed.assistant_message_id;
        assistantText += parsed.text;
        setMessages((items) => {
          const previous = items.find((item) => item.id === assistantId);
          const partial: Message = {
            id: assistantId,
            conversation_id: conversationId,
            role: "assistant",
            text: assistantText,
            attachment_ids: [],
            state: "processing",
            created_at: previous?.created_at ?? new Date().toISOString(),
          };
          return previous
            ? items.map((item) => (item.id === assistantId ? partial : item))
            : [...items, partial];
        });
      } else if (parsed.type === "done") {
        completed = true;
        setMessages((items) => [...items.filter((item) => item.id !== assistantId), parsed.assistant_message]);
        setAttachments([]);
      } else if (parsed.type === "error") {
        throw new ApiError(502, parsed.message);
      }
    };
    let expectedSequence = 1;
    try {
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value, { stream: !done });
        let delimiter = /\r?\n\r?\n/.exec(buffer);
        while (delimiter) {
          const boundary = delimiter.index;
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + delimiter[0].length);
          if (frame) {
            let parsedData = "";
            let eventName = "";
            for (const line of frame.split(/\r?\n/)) {
              if (line.startsWith("event:")) eventName = line.slice(6).trim();
              if (line.startsWith("data:")) parsedData += line.slice(5).trim();
            }
            const parsed = streamEvent.parse(JSON.parse(parsedData)) as StreamEvent;
            if (parsed.type !== eventName) throw new Error("Mismatched streaming event");
            if (parsed.type === "delta") {
              if (parsed.sequence !== expectedSequence++) throw new Error("Invalid delta sequence");
            }
            handleFrame(frame);
          }
          delimiter = /\r?\n\r?\n/.exec(buffer);
        }
        if (done) break;
      }
      if (buffer.trim()) throw new Error("Incomplete streaming event");
      if (!completed) throw new Error("Stream ended before completion");
    } finally {
      reader.releaseLock();
    }
  }

  const send = useCallback(async (retry?: {
    text: string;
    attachment_ids: string[];
    client_request_id: string;
  }) => {
    if (processing) return;
    const request = retry ?? {
      text: draft,
      attachment_ids: attachments.map((item) => item.id),
      client_request_id: uuid(),
    };
    if (!request.text.trim() && request.attachment_ids.length === 0) return;
    const conversationId = activeConversation ?? (await createConversation());
    setProcessing(true);
    setError("");
    setLastRequest(request);
    if (!retry) setDraft("");
    abortRef.current = new AbortController();
    try {
      const response = await fetch(`/api/v1/conversations/${conversationId}/messages`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": identity?.csrf_token ?? "",
        },
        body: JSON.stringify(request),
        signal: abortRef.current.signal,
      });
      await consumeStream(response, request, conversationId);
    } catch (cause) {
      if (!(cause instanceof DOMException && cause.name === "AbortError")) {
        setError(
          cause instanceof ApiError
            ? cause.message
            : "The response could not be safely processed. Please retry.",
        );
      }
    } finally {
      setProcessing(false);
      abortRef.current = undefined;
    }
  }, [activeConversation, attachments, createConversation, draft, identity?.csrf_token, processing]);

  async function selectConversation(id: string) {
    setActiveConversation(id);
    setError("");
    try {
      await loadMessages(id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load messages");
    }
  }

  return {
    conversations,
    activeConversation,
    messages,
    attachments,
    draft,
    setDraft,
    processing,
    loading,
    error,
    lastRequest,
    send,
    retry: () => lastRequest && void send(lastRequest),
    uploadFile,
    uploadFileWithStatus,
    addAttachment,
    removeAttachment,
    selectConversation,
    newConversation: createConversation,
    cancel: () => abortRef.current?.abort(),
  };
}

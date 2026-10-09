import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";
import { LoadingIndicator } from "../../components/LoadingIndicator";
import type { Attachment, DemoSample } from "../../lib/schemas";
import { AttachmentList } from "./AttachmentList";
import { AttachmentMenu } from "./AttachmentMenu";

export function ChatComposer({
  draft,
  setDraft,
  attachments,
  onRemoveAttachment,
  onUpload,
  onSend,
  onCancel,
  processing,
  samples,
  samplesLoading,
  samplesError,
  selectingSample,
  onSelectSample,
  onRetrySamples,
  error,
  onRetry,
  retryAvailable,
}: {
  draft: string;
  setDraft: (value: string) => void;
  attachments: Attachment[];
  onRemoveAttachment: (id: string) => void;
  onUpload: (file: File) => void;
  onSend: () => void;
  onCancel: () => void;
  processing: boolean;
  samples: DemoSample[];
  samplesLoading: boolean;
  samplesError: string;
  selectingSample: string | null;
  onSelectSample: (sample: DemoSample) => void;
  onRetrySamples: () => void;
  error: string;
  onRetry: () => void;
  retryAvailable: boolean;
}) {
  const textarea = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (textarea.current) {
      textarea.current.style.height = "auto";
      textarea.current.style.height = `${Math.min(textarea.current.scrollHeight, 180)}px`;
    }
  }, [draft]);
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!processing) onSend();
  }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!processing) onSend();
    }
  }
  return (
    <div>
      {error && (
        <div className="chat-error" role="alert">
          <span>{error}</span>
          {retryAvailable && (
            <button type="button" disabled={processing} onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      )}
      {processing && <LoadingIndicator label="Preparing your response…" />}
      <AttachmentList
        attachments={attachments}
        onRemove={onRemoveAttachment}
        disabled={processing}
      />
      <form className="chat-composer" onSubmit={submit}>
        <AttachmentMenu
          onUpload={onUpload}
          samples={samples}
          loading={samplesLoading}
          error={samplesError}
          selecting={selectingSample}
          onSelectSample={onSelectSample}
          onRetrySamples={onRetrySamples}
          disabled={processing}
        />
        <textarea
          ref={textarea}
          aria-label="Message"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={keyDown}
          placeholder="Message"
          maxLength={100_000}
          disabled={processing}
          rows={1}
        />
        {processing ? (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        ) : (
          <button
            type="submit"
            className="send-button"
            aria-label="Send"
            title="Send message"
            disabled={!draft.trim() && attachments.length === 0}
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M12 19V5M6 11l6-6 6 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}
      </form>
    </div>
  );
}

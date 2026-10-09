import { useRef, type FormEvent, type KeyboardEvent } from "react";
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
            <button type="button" disabled={processing} onClick={onRetry}>Retry</button>
          )}
        </div>
      )}
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
          rows={2}
        />
        {processing ? (
          <button type="button" onClick={onCancel}>Cancel</button>
        ) : (
          <button type="submit" disabled={!draft.trim() && attachments.length === 0}>
            Send
          </button>
        )}
      </form>
    </div>
  );
}

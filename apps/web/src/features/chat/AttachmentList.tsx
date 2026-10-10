import type { Attachment } from "../../lib/schemas";

export function AttachmentList({
  attachments,
  onRemove,
  disabled = false,
}: {
  attachments: Attachment[];
  onRemove: (id: string) => void;
  disabled?: boolean;
}) {
  if (!attachments.length) return null;
  return (
    <ul className="attachment-list" aria-label="Attached files">
      {attachments.map((item) => (
        <li key={item.id}>
          <span>{item.filename}</span>
          <span>{item.state}</span>
          <button
            type="button"
            disabled={disabled}
            aria-label={`Remove ${item.filename}`}
            onClick={() => onRemove(item.id)}
          >
            Remove
          </button>
        </li>
      ))}
    </ul>
  );
}

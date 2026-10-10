import { useEffect, useRef, useState } from "react";
import type { Attachment, DemoSample } from "../../lib/schemas";
import { DemoSamplePicker } from "./DemoSamplePicker";

export function AttachmentMenu({
  onUpload,
  samples,
  loading,
  error,
  selecting,
  onSelectSample,
  onRetrySamples,
  disabled,
}: {
  onUpload: (file: File) => void;
  samples: DemoSample[];
  loading: boolean;
  error: string;
  selecting: string | null;
  onSelectSample: (sample: DemoSample) => void;
  onRetrySamples: () => void;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [showSamples, setShowSamples] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menuButton.current?.focus();
      }
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    root.current?.querySelector<HTMLButtonElement>("[role=menuitem]")?.focus();
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);
  return (
    <div ref={root} className="attachment-menu">
      <button
        ref={menuButton}
        type="button"
        aria-label="Add attachment"
        aria-expanded={open}
        aria-haspopup="menu"
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
      >
        Add
      </button>
      {open && (
        <div
          className="attachment-menu-popover"
          role="menu"
          aria-label="Attachment options"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setOpen(false);
              menuButton.current?.focus();
            }
          }}
        >
          <button
            type="button"
            role="menuitem"
            disabled={disabled}
            onClick={() => fileInput.current?.click()}
          >
            Upload file
          </button>
          <input
            ref={fileInput}
            aria-label="Upload file"
            type="file"
            accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg"
            disabled={disabled}
            hidden
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onUpload(file);
              event.currentTarget.value = "";
              setOpen(false);
            }}
          />
          <button
            type="button"
            role="menuitem"
            aria-expanded={showSamples}
            onClick={() => setShowSamples((value) => !value)}
          >
            Try test data
          </button>
          {showSamples && (
            <DemoSamplePicker
              samples={samples}
              loading={loading}
              error={error}
              selecting={selecting}
              onSelect={(sample) => {
                onSelectSample(sample);
                setOpen(false);
              }}
              onRetry={onRetrySamples}
            />
          )}
        </div>
      )}
    </div>
  );
}

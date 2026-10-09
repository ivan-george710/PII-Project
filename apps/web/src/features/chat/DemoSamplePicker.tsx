import type { DemoSample } from "../../lib/schemas";

const groupFor = (sample: DemoSample) => {
  if (sample.kind === "message") return "Message";
  if (sample.mime_type === "application/pdf") return "PDF";
  if (sample.mime_type.includes("wordprocessing")) return "Word";
  if (sample.mime_type.includes("presentation")) return "PowerPoint";
  return "Image";
};

const tagText: Record<string, string> = {
  text_pii: "Text PII",
  scanned_text: "Scanned text",
  faces: "Embedded faces",
  custom_rules: "Custom rules",
};

export function DemoSamplePicker({
  samples,
  loading,
  error,
  selecting,
  onSelect,
  onRetry,
}: {
  samples: DemoSample[];
  loading: boolean;
  error: string;
  selecting: string | null;
  onSelect: (sample: DemoSample) => void;
  onRetry: () => void;
}) {
  const groups = ["Message", "PDF", "Word", "PowerPoint", "Image"];
  return (
    <div className="sample-picker" role="region" aria-label="Try test data">
      <h3>Try test data</h3>
      {loading && <p role="status">Loading samples…</p>}
      {error && (
        <div role="alert">
          <span>{error}</span>
          <button type="button" onClick={onRetry}>Retry</button>
        </div>
      )}
      {!loading &&
        groups.map((group) => {
          const items = samples.filter((sample) => groupFor(sample) === group);
          return items.length ? (
            <section key={group} aria-label={`${group} examples`}>
              <h4>{group}</h4>
              {items.map((sample) => (
                <button
                  key={sample.id}
                  type="button"
                  disabled={selecting !== null}
                  onClick={() => onSelect(sample)}
                >
                  <strong>{sample.title}</strong>
                  <span>{sample.description}</span>
                  <small>{sample.tags.map((tag) => tagText[tag]).join(", ")}</small>
                  {selecting === sample.id && <span role="status">Adding…</span>}
                </button>
              ))}
            </section>
          ) : null;
        })}
    </div>
  );
}

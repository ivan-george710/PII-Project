import { useState } from "react";
import { rulePreviewInput, rulePreviewResult } from "../../lib/schemas";
import { z } from "zod";

type PreviewResult = z.infer<typeof rulePreviewResult>;

export function RulePreview({
  onPreview,
}: {
  onPreview: (data: {
    kind: "exact" | "regex";
    pattern: string;
    case_sensitive: boolean;
    sample_text: string;
  }) => Promise<{
    matches: { start: number; end: number }[];
    count: number;
    truncated: boolean;
  }>;
}) {
  const [kind, setKind] = useState<"exact" | "regex">("exact");
  const [pattern, setPattern] = useState("");
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [sampleText, setSampleText] = useState("");
  const [result, setResult] = useState<{
    matches: { start: number; end: number }[];
    count: number;
    truncated: boolean;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const handleTest = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    const validation = rulePreviewInput.safeParse({
      kind,
      pattern,
      case_sensitive: caseSensitive,
      sample_text: sampleText,
    });

    if (!validation.success) {
      setError(validation.error.issues[0]?.message || "Invalid preview input");
      return;
    }

    setTesting(true);
    try {
      const res = await onPreview(validation.data);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview evaluation failed");
    } finally {
      setTesting(false);
    }
  };

  return (
    <section>
      <h2>Rule Preview Sandbox</h2>
      <p>Test patterns against sample text before saving. No data is stored.</p>
      {error && <p role="alert">{error}</p>}

      <form onSubmit={handleTest}>
        <div>
          <label htmlFor="preview-kind">Kind</label>
          <select
            id="preview-kind"
            value={kind}
            onChange={(e) => setKind(e.target.value as "exact" | "regex")}
          >
            <option value="exact">Exact Phrase</option>
            <option value="regex">Regular Expression</option>
          </select>
        </div>

        <div>
          <label htmlFor="preview-pattern">Pattern</label>
          <input
            id="preview-pattern"
            type="text"
            value={pattern}
            onChange={(e) => setPattern(e.target.value)}
            maxLength={512}
            required
          />
        </div>

        <div>
          <label>
            <input
              type="checkbox"
              checked={caseSensitive}
              onChange={(e) => setCaseSensitive(e.target.checked)}
            />
            Case sensitive
          </label>
        </div>

        <div>
          <label htmlFor="preview-sample-text">Sample text (max 10,000 chars)</label>
          <textarea
            id="preview-sample-text"
            value={sampleText}
            onChange={(e) => setSampleText(e.target.value)}
            maxLength={10000}
            rows={4}
            style={{ width: "100%" }}
            required
          />
        </div>

        <button type="submit" disabled={testing}>
          {testing ? "Testing…" : "Test pattern"}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: "1rem" }} role="status">
          <h3>Test Results</h3>
          <p>
            Matches found: <strong>{result.count}</strong>
            {result.truncated && " (display capped at 1,000 matches)"}
          </p>
          {result.matches.length > 0 && (
            <ul>
              {result.matches.slice(0, 10).map((m, idx) => (
                <li key={idx}>
                  Offset {m.start} to {m.end}
                </li>
              ))}
              {result.matches.length > 10 && (
                <li>…and {result.matches.length - 10} more</li>
              )}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

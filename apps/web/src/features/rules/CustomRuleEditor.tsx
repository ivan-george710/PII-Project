import { useState } from "react";
import { createCustomRuleInput, updateCustomRuleInput, type CustomRule } from "../../lib/schemas";

export function CustomRuleEditor({
  customRules,
  expectedVersion,
  saving,
  onCreate,
  onUpdate,
  onDelete,
}: {
  customRules: CustomRule[];
  expectedVersion: number;
  saving: boolean;
  onCreate: (data: {
    name: string;
    kind: "exact" | "regex";
    pattern: string;
    case_sensitive: boolean;
    enabled: boolean;
  }) => Promise<void>;
  onUpdate: (
    id: string,
    data: {
      name?: string;
      kind?: "exact" | "regex";
      pattern?: string;
      case_sensitive?: boolean;
      enabled?: boolean;
    }
  ) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"exact" | "regex">("exact");
  const [pattern, setPattern] = useState("");
  const [caseSensitive, setCaseSensitive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validation = createCustomRuleInput.safeParse({
      expected_version: expectedVersion,
      name,
      kind,
      pattern,
      case_sensitive: caseSensitive,
      enabled: true,
    });

    if (!validation.success) {
      setError(validation.error.issues[0]?.message || "Invalid custom rule");
      return;
    }

    try {
      await onCreate(validation.data);
      setName("");
      setPattern("");
      setKind("exact");
      setCaseSensitive(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    }
  };

  return (
    <section>
      <h2>Custom Rules ({customRules.length}/100)</h2>

      {customRules.length === 0 ? (
        <p>No custom rules defined.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {customRules.map((rule) => (
            <li
              key={rule.id}
              style={{
                border: "1px solid #ccc",
                padding: "0.75rem",
                marginBottom: "0.5rem",
              }}
            >
              <div>
                <strong>{rule.name}</strong> ({rule.kind}
                {rule.case_sensitive ? ", case sensitive" : ""})
              </div>
              <code style={{ display: "block", margin: "0.25rem 0" }}>
                {rule.pattern}
              </code>
              <div>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() =>
                    void onUpdate(rule.id, { enabled: !rule.enabled })
                  }
                >
                  {rule.enabled ? "Enabled" : "Disabled"}
                </button>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void onDelete(rule.id)}
                  style={{ marginLeft: "0.5rem" }}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {customRules.length < 100 && (
        <form onSubmit={handleSubmit} style={{ marginTop: "1rem" }}>
          <h3>Add Custom Rule</h3>
          {error && <p role="alert">{error}</p>}

          <div>
            <label htmlFor="custom-rule-name">Name</label>
            <input
              id="custom-rule-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={80}
              required
            />
          </div>

          <div>
            <label htmlFor="custom-rule-kind">Kind</label>
            <select
              id="custom-rule-kind"
              value={kind}
              onChange={(e) => setKind(e.target.value as "exact" | "regex")}
            >
              <option value="exact">Exact Phrase</option>
              <option value="regex">Regular Expression</option>
            </select>
          </div>

          <div>
            <label htmlFor="custom-rule-pattern">Pattern</label>
            <input
              id="custom-rule-pattern"
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

          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Add custom rule"}
          </button>
        </form>
      )}
    </section>
  );
}

import { useState } from "react";
import { organizationInput } from "../../lib/schemas";
export function OrganizationForm({
  name,
  save,
}: {
  name: string;
  save: (name: string) => Promise<void>;
}) {
  const [value, setValue] = useState(name);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  return (
    <form
      className="organization-form"
      onSubmit={async (e) => {
        e.preventDefault();
        const result = organizationInput.safeParse({ name: value });
        if (!result.success) {
          setError("Enter a company name (1–120 characters).");
          return;
        }
        setSaving(true);
        setError("");
        try {
          await save(result.data.name);
        } catch (e) {
          setError(e instanceof Error ? e.message : "Could not save");
        } finally {
          setSaving(false);
        }
      }}
    >
      <label htmlFor="company-name">Company name</label>
      <input
        id="company-name"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        maxLength={120}
      />
      <button disabled={saving}>{saving ? "Saving…" : "Save"}</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}

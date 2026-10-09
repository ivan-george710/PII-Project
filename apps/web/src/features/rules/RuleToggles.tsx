import { type PolicySnapshot, type RuleId } from "../../lib/schemas";

const BUILTIN_NAMES: Record<RuleId, string> = {
  PERSON: "Person Names",
  EMAIL_ADDRESS: "Email Addresses",
  PHONE_NUMBER: "Phone Numbers",
  EMPLOYEE_ID: "Employee IDs",
  US_SSN: "US Social Security Numbers",
  US_PASSPORT: "US Passports",
  US_DRIVER_LICENSE: "US Driver's Licenses",
  US_ITIN: "US Taxpayer IDs (ITIN)",
  US_BANK_NUMBER: "US Bank Numbers",
  IBAN_CODE: "IBAN Codes",
  CREDIT_CARD: "Credit & Debit Cards",
  MEDICAL_LICENSE: "Medical Licenses",
  FACE: "Face Detection",
};

export function RuleToggles({
  policy,
  saving,
  onToggleBuiltin,
  onToggleAll,
}: {
  policy: PolicySnapshot;
  saving: boolean;
  onToggleBuiltin: (ruleId: RuleId, enabled: boolean) => Promise<void>;
  onToggleAll: (enabled: boolean) => Promise<void>;
}) {
  const builtinEntries = Object.entries(policy.builtins) as [RuleId, boolean][];
  const allEnabled =
    builtinEntries.every(([, val]) => val) &&
    policy.custom_rules.every((r) => r.enabled);

  return (
    <section>
      <h2>Built-in Rules</h2>
      <div style={{ marginBottom: "1rem" }}>
        <button
          type="button"
          disabled={saving}
          onClick={() => void onToggleAll(!allEnabled)}
        >
          {allEnabled ? "Disable all rules" : "Enable all rules"}
        </button>
      </div>

      <fieldset disabled={saving}>
        <legend>Individual Toggles</legend>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {builtinEntries.map(([ruleId, enabled]) => (
            <li
              key={ruleId}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "0.5rem 0",
                borderBottom: "1px solid #ccc",
              }}
            >
              <span>{BUILTIN_NAMES[ruleId] || ruleId}</span>
              <button
                type="button"
                onClick={() => void onToggleBuiltin(ruleId, !enabled)}
              >
                {enabled ? "Enabled" : "Disabled"}
              </button>
            </li>
          ))}
        </ul>
      </fieldset>
    </section>
  );
}

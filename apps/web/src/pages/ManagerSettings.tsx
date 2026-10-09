import { CustomRuleEditor } from "../features/rules/CustomRuleEditor";
import { RulePreview } from "../features/rules/RulePreview";
import { RuleToggles } from "../features/rules/RuleToggles";
import { useRules } from "../features/rules/useRules";

export default function ManagerSettings() {
  const {
    policy,
    loading,
    error,
    conflict,
    saving,
    reload,
    updateBuiltin,
    toggleAll,
    createCustomRule,
    updateCustomRule,
    deleteCustomRule,
    previewRule,
  } = useRules();

  if (loading) return <p role="status">Loading company rules…</p>;

  if (error && !policy) {
    return (
      <section>
        <h1>Company Rules & Settings</h1>
        <p role="alert">{error}</p>
        <button onClick={() => void reload()}>Retry</button>
      </section>
    );
  }

  if (!policy) return null;

  return (
    <section>
      <header>
        <h1>Company Rules & Settings</h1>
        <p>Policy version: {policy.version}</p>
      </header>

      {conflict && (
        <div
          role="alert"
          style={{
            border: "2px solid #000",
            padding: "0.75rem",
            marginBottom: "1rem",
            backgroundColor: "#eee",
          }}
        >
          <p>
            <strong>Version Conflict:</strong> Settings were modified by another
            manager. Please reload before saving further changes.
          </p>
          <button onClick={() => void reload()}>Reload latest settings</button>
        </div>
      )}

      {error && !conflict && <p role="alert">{error}</p>}

      <RuleToggles
        policy={policy}
        saving={saving}
        onToggleBuiltin={updateBuiltin}
        onToggleAll={toggleAll}
      />

      <hr style={{ margin: "1.5rem 0" }} />

      <CustomRuleEditor
        customRules={policy.custom_rules}
        expectedVersion={policy.version}
        saving={saving}
        onCreate={createCustomRule}
        onUpdate={updateCustomRule}
        onDelete={deleteCustomRule}
      />

      <hr style={{ margin: "1.5rem 0" }} />

      <RulePreview onPreview={previewRule} />
    </section>
  );
}

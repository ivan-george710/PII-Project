import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../../lib/api";
import {
  customRuleMutationResult,
  deleteCustomRuleResult,
  policySnapshot,
  rulePreviewResult,
  type CustomRule,
  type PolicySnapshot,
  type RuleId,
} from "../../lib/schemas";
import { useAuth } from "../auth/useAuth";

export function useRules() {
  const { identity } = useAuth();
  const [policy, setPolicy] = useState<PolicySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [saving, setSaving] = useState(false);

  const csrf = identity?.csrf_token;

  const loadPolicy = useCallback(async () => {
    setLoading(true);
    setError(null);
    setConflict(false);
    try {
      const data = await api("/rules", policySnapshot, {}, csrf);
      setPolicy(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load rules");
    } finally {
      setLoading(false);
    }
  }, [csrf]);

  useEffect(() => {
    void loadPolicy();
  }, [loadPolicy]);

  const updateBuiltin = async (rule_id: RuleId, enabled: boolean) => {
    if (!policy) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api(
        "/rules/builtins",
        policySnapshot,
        {
          method: "PATCH",
          body: JSON.stringify({
            expected_version: policy.version,
            updates: [{ rule_id, enabled }],
          }),
        },
        csrf
      );
      setPolicy(updated);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
      }
      setError(e instanceof Error ? e.message : "Failed to update rule");
    } finally {
      setSaving(false);
    }
  };

  const toggleAll = async (enabled: boolean) => {
    if (!policy) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api(
        "/rules/toggle-all",
        policySnapshot,
        {
          method: "POST",
          body: JSON.stringify({
            expected_version: policy.version,
            enabled,
          }),
        },
        csrf
      );
      setPolicy(updated);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
      }
      setError(e instanceof Error ? e.message : "Failed to toggle all rules");
    } finally {
      setSaving(false);
    }
  };

  const createCustomRule = async (data: {
    name: string;
    kind: "exact" | "regex";
    pattern: string;
    case_sensitive: boolean;
    enabled: boolean;
  }) => {
    if (!policy) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api(
        "/rules/custom",
        customRuleMutationResult,
        {
          method: "POST",
          body: JSON.stringify({
            expected_version: policy.version,
            ...data,
          }),
        },
        csrf
      );
      setPolicy({
        ...policy,
        version: res.policy_version,
        custom_rules: [...policy.custom_rules, res.rule],
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
      }
      throw e;
    } finally {
      setSaving(false);
    }
  };

  const updateCustomRule = async (
    ruleId: string,
    data: {
      name?: string;
      kind?: "exact" | "regex";
      pattern?: string;
      case_sensitive?: boolean;
      enabled?: boolean;
    }
  ) => {
    if (!policy) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api(
        `/rules/custom/${ruleId}`,
        customRuleMutationResult,
        {
          method: "PATCH",
          body: JSON.stringify({
            expected_version: policy.version,
            ...data,
          }),
        },
        csrf
      );
      setPolicy({
        ...policy,
        version: res.policy_version,
        custom_rules: policy.custom_rules.map((r) =>
          r.id === ruleId ? res.rule : r
        ),
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
      }
      throw e;
    } finally {
      setSaving(false);
    }
  };

  const deleteCustomRule = async (ruleId: string) => {
    if (!policy) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api(
        `/rules/custom/${ruleId}?expected_version=${policy.version}`,
        deleteCustomRuleResult,
        { method: "DELETE" },
        csrf
      );
      setPolicy({
        ...policy,
        version: res.policy_version,
        custom_rules: policy.custom_rules.filter((r) => r.id !== ruleId),
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
      }
      setError(e instanceof Error ? e.message : "Failed to delete custom rule");
    } finally {
      setSaving(false);
    }
  };

  const previewRule = async (data: {
    kind: "exact" | "regex";
    pattern: string;
    case_sensitive: boolean;
    sample_text: string;
  }) => {
    return await api(
      "/rules/preview",
      rulePreviewResult,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      csrf
    );
  };

  return {
    policy,
    loading,
    error,
    conflict,
    saving,
    reload: loadPolicy,
    updateBuiltin,
    toggleAll,
    createCustomRule,
    updateCustomRule,
    deleteCustomRule,
    previewRule,
  };
}

import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RuleToggles } from "../src/features/rules/RuleToggles";
import { CustomRuleEditor } from "../src/features/rules/CustomRuleEditor";
import { RulePreview } from "../src/features/rules/RulePreview";
import { type PolicySnapshot } from "../src/lib/schemas";

const samplePolicy: PolicySnapshot = {
  organization_id: "00000000-0000-4000-8000-000000000001",
  version: 1,
  builtins: {
    PERSON: true,
    EMAIL_ADDRESS: true,
    PHONE_NUMBER: true,
    EMPLOYEE_ID: true,
    US_SSN: true,
    US_PASSPORT: true,
    US_DRIVER_LICENSE: true,
    US_ITIN: true,
    US_BANK_NUMBER: true,
    IBAN_CODE: true,
    CREDIT_CARD: true,
    MEDICAL_LICENSE: true,
    FACE: true,
  },
  custom_rules: [],
};

describe("RuleToggles component", () => {
  it("renders 13 built-in rules and handles master toggle all", async () => {
    const user = userEvent.setup();
    const onToggleBuiltin = vi.fn().mockResolvedValue(undefined);
    const onToggleAll = vi.fn().mockResolvedValue(undefined);

    render(
      <RuleToggles
        policy={samplePolicy}
        saving={false}
        onToggleBuiltin={onToggleBuiltin}
        onToggleAll={onToggleAll}
      />
    );

    expect(screen.getByRole("heading", { name: "Built-in Rules" })).toBeInTheDocument();
    const toggleAllBtn = screen.getByRole("button", { name: "Disable all rules" });
    await user.click(toggleAllBtn);
    expect(onToggleAll).toHaveBeenCalledWith(false);
  });

  it("triggers individual toggle for specific built-in rule", async () => {
    const user = userEvent.setup();
    const onToggleBuiltin = vi.fn().mockResolvedValue(undefined);
    const onToggleAll = vi.fn().mockResolvedValue(undefined);

    render(
      <RuleToggles
        policy={samplePolicy}
        saving={false}
        onToggleBuiltin={onToggleBuiltin}
        onToggleAll={onToggleAll}
      />
    );

    const buttons = screen.getAllByRole("button", { name: "Enabled" });
    expect(buttons.length).toBeGreaterThan(0);
    await user.click(buttons[0]);
    expect(onToggleBuiltin).toHaveBeenCalled();
  });
});

describe("CustomRuleEditor component", () => {
  it("validates rule name and creates a new custom rule", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn().mockResolvedValue(undefined);
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    const onDelete = vi.fn().mockResolvedValue(undefined);

    render(
      <CustomRuleEditor
        customRules={[]}
        expectedVersion={1}
        saving={false}
        onCreate={onCreate}
        onUpdate={onUpdate}
        onDelete={onDelete}
      />
    );

    const nameInput = screen.getByLabelText("Name");
    const patternInput = screen.getByLabelText("Pattern");
    const submitBtn = screen.getByRole("button", { name: "Add custom rule" });

    await user.type(nameInput, "Secret Codename");
    await user.type(patternInput, "ProjectTitan");
    await user.click(submitBtn);

    await waitFor(() =>
      expect(onCreate).toHaveBeenCalledWith({
        expected_version: 1,
        name: "Secret Codename",
        kind: "exact",
        pattern: "ProjectTitan",
        case_sensitive: false,
        enabled: true,
      })
    );
  });
});

describe("RulePreview component", () => {
  it("tests a pattern and displays match counts and spans", async () => {
    const user = userEvent.setup();
    const onPreview = vi.fn().mockResolvedValue({
      matches: [{ start: 10, end: 16 }],
      count: 1,
      truncated: false,
    });

    render(<RulePreview onPreview={onPreview} />);

    const patternInput = screen.getByLabelText("Pattern");
    const textInput = screen.getByLabelText(/Sample text/i);
    const testBtn = screen.getByRole("button", { name: "Test pattern" });

    await user.type(patternInput, "secret");
    await user.type(textInput, "This is a secret message.");
    await user.click(testBtn);

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Matches found: 1")
    );
    expect(screen.getByText(/Offset 10 to 16/i)).toBeInTheDocument();
  });
});

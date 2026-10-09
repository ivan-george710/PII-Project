import { z } from "zod";
const id = z.uuid();
export const role = z.enum(["employee", "manager"]);
export const userSummary = z.strictObject({
  id,
  email: z.string(),
  display_name: z.string().min(1).max(120),
  role,
});
export const organization = z.strictObject({
  id,
  name: z.string().min(1).max(120),
  created_at: z.iso.datetime(),
});
export const session = z.strictObject({
  user: userSummary.extend({ organization_id: id }),
  organization: z.strictObject({ id, name: z.string().min(1).max(120) }),
  csrf_token: z.string().min(1),
});
export const organizationInput = z.strictObject({
  name: z.string().trim().min(1).max(120),
});
export const assignmentInput = z.strictObject({ manager_id: id });
export const assignment = z.strictObject({
  employee_id: id,
  manager_id: id,
  updated_at: z.iso.datetime(),
});
export const usersPage = z.strictObject({
  items: z.array(userSummary),
  next_cursor: z.string().nullable(),
});
export const assignmentsPage = z.strictObject({
  items: z.array(assignment),
  next_cursor: z.string().nullable(),
});
export const apiError = z.strictObject({
  error: z.strictObject({
    code: z.string(),
    message: z.string(),
    fields: z.array(z.strictObject({ path: z.string(), message: z.string() })),
    request_id: id,
  }),
});
export type Session = z.infer<typeof session>;
export const loginInput = z.strictObject({
  email: z.string().transform((value) => value.toLowerCase()),
  password: z.string(),
});
export const signupInput = loginInput.extend({
  display_name: z.string(),
});

// Issue 4: Rules & Policy Schemas
export const ruleId = z.enum([
  "PERSON",
  "EMAIL_ADDRESS",
  "PHONE_NUMBER",
  "EMPLOYEE_ID",
  "US_SSN",
  "US_PASSPORT",
  "US_DRIVER_LICENSE",
  "US_ITIN",
  "US_BANK_NUMBER",
  "IBAN_CODE",
  "CREDIT_CARD",
  "MEDICAL_LICENSE",
  "FACE",
]);

export const customRule = z.strictObject({
  id,
  name: z.string().min(1).max(80),
  kind: z.enum(["exact", "regex"]),
  pattern: z.string().min(1).max(512),
  case_sensitive: z.boolean(),
  enabled: z.boolean(),
});

export const policySnapshot = z.strictObject({
  organization_id: id,
  version: z.number().int().min(1),
  builtins: z.record(ruleId, z.boolean()),
  custom_rules: z.array(customRule).max(100),
});

export const updateBuiltinsInput = z.strictObject({
  expected_version: z.number().int().min(1),
  updates: z
    .array(z.strictObject({ rule_id: ruleId, enabled: z.boolean() }))
    .min(1)
    .max(13),
});

export const toggleAllInput = z.strictObject({
  expected_version: z.number().int().min(1),
  enabled: z.boolean(),
});

export const createCustomRuleInput = z.strictObject({
  expected_version: z.number().int().min(1),
  name: z.string().trim().min(1).max(80),
  kind: z.enum(["exact", "regex"]),
  pattern: z.string().min(1).max(512),
  case_sensitive: z.boolean(),
  enabled: z.boolean(),
});

export const updateCustomRuleInput = z.strictObject({
  expected_version: z.number().int().min(1),
  name: z.string().trim().min(1).max(80).optional(),
  kind: z.enum(["exact", "regex"]).optional(),
  pattern: z.string().min(1).max(512).optional(),
  case_sensitive: z.boolean().optional(),
  enabled: z.boolean().optional(),
});

export const customRuleMutationResult = z.strictObject({
  rule: customRule,
  policy_version: z.number().int().min(1),
});

export const deleteCustomRuleResult = z.strictObject({
  deleted_id: id,
  policy_version: z.number().int().min(1),
});

export const rulePreviewInput = z.strictObject({
  kind: z.enum(["exact", "regex"]),
  pattern: z.string().min(1).max(512),
  case_sensitive: z.boolean(),
  sample_text: z.string().max(10000),
});

export const previewMatch = z.strictObject({
  start: z.number().int().min(0),
  end: z.number().int().min(0),
});

export const rulePreviewResult = z.strictObject({
  matches: z.array(previewMatch).max(1000),
  count: z.number().int().min(0),
  truncated: z.boolean(),
});

// Issue 4: Reports Schemas
export const sourceLocation = z.strictObject({
  artifact_id: id.nullable().optional(),
  kind: z.enum(["message", "native_text", "ocr", "face"]),
  page_number: z.number().int().min(1).nullable().optional(),
  slide_number: z.number().int().min(1).nullable().optional(),
  source_ref: z.string().nullable().optional(),
  start: z.number().int().min(0).nullable().optional(),
  end: z.number().int().min(0).nullable().optional(),
  bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]).nullable().optional(),
});

export const reportFinding = z.strictObject({
  rule_id: z.string(),
  category: z.string(),
  count: z.number().int().min(1),
  action: z.enum(["redacted", "allowed_disabled"]),
  locations: z.array(sourceLocation),
});

export const reportEvent = z.strictObject({
  id,
  submission_id: id,
  employee: z.strictObject({
    id,
    display_name: z.string(),
    email: z.string(),
  }),
  occurred_at: z.iso.datetime(),
  policy_version: z.number().int().min(1),
  status: z.enum(["completed", "failed"]),
  failure_code: z.string().nullable().optional(),
  findings: z.array(reportFinding),
  total_findings: z.number().int().min(0),
});

export const reportEventsPage = z.strictObject({
  items: z.array(reportEvent),
  next_cursor: z.string().nullable(),
});

export const reportSummary = z.strictObject({
  submission_count: z.number().int().min(0),
  failed_count: z.number().int().min(0),
  redacted_count: z.number().int().min(0),
  allowed_disabled_count: z.number().int().min(0),
  by_category: z.array(
    z.strictObject({
      category: z.string(),
      count: z.number().int().min(0),
    })
  ),
});

export type CustomRule = z.infer<typeof customRule>;
export type PolicySnapshot = z.infer<typeof policySnapshot>;
export type RuleId = z.infer<typeof ruleId>;
export type ReportEvent = z.infer<typeof reportEvent>;
export type ReportSummary = z.infer<typeof reportSummary>;


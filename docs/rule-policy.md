# Rule Policy Specification

This document defines company-wide privacy rule policies, built-in rule identifiers, versioning semantics, and custom rule constraints for PII Guard.

## Built-In Rules

Every company policy contains the following 13 built-in rules, identified by standard IDs:

| Rule ID | Category | Description |
|---|---|---|
| `PERSON` | Personal Identity | Individual names |
| `EMAIL_ADDRESS` | Contact Info | Email addresses |
| `PHONE_NUMBER` | Contact Info | Telephone numbers |
| `EMPLOYEE_ID` | Organization | Internal company employee identifiers |
| `US_SSN` | Government ID | United States Social Security Numbers |
| `US_PASSPORT` | Government ID | United States Passport Numbers |
| `US_DRIVER_LICENSE` | Government ID | State Driver's License Numbers |
| `US_ITIN` | Government ID | Individual Taxpayer Identification Numbers |
| `US_BANK_NUMBER` | Financial | Bank account routing / account numbers |
| `IBAN_CODE` | Financial | International Bank Account Numbers |
| `CREDIT_CARD` | Financial | Credit and debit card numbers |
| `MEDICAL_LICENSE` | Professional | Medical license numbers |
| `FACE` | Biometric | Detected human facial regions |

### Default State
When a company is created or initialized, all 13 built-in rules are enabled by default (`enabled: true`), and the initial policy `version` is `1`.

---

## Policy Versioning & Optimistic Concurrency

1. **Version Monotonicity**:
   - Initial policy version is `1`.
   - Any mutation (updating built-in toggles, master toggle-all, adding, updating, or deleting a custom rule) **atomically increments the version by exactly 1**.
2. **Optimistic Concurrency Control**:
   - All update endpoints require an `expected_version: int`.
   - If the current stored policy version does not match `expected_version`, the server rejects the request with HTTP `409 Conflict` and code `POLICY_VERSION_CONFLICT`.
   - Clients must reload the policy snapshot before re-applying changes.

---

## Custom Rules

Companies can define up to **100 custom rules**.

### Schema
Each custom rule contains:
- `id`: UUID string. Internal rule identity in events is formatted as `custom:<uuid>`.
- `name`: 1 to 80 characters, trimmed of leading/trailing whitespace. Names must be unique within a company's custom rules.
- `kind`: `"exact"` (literal string matching) or `"regex"` (regular expression pattern).
- `pattern`: 1 to 512 characters. Whitespace-only patterns are rejected.
- `case_sensitive`: Strict boolean flag.
- `enabled`: Strict boolean flag.

### Execution Constraints & Regex Safeguards
1. **Empty-String Matching**: Regex patterns that match an empty string (e.g. `.*`, `^$`, `a*`) are strictly forbidden and rejected with HTTP `422`.
2. **Regex Timeout Protection**: To prevent Regular Expression Denial of Service (ReDoS), evaluation runs with a bounded execution limit (100ms per unit). Exceeding this limit returns HTTP `422` with code `RULE_TIMEOUT`.
3. **Safe Preview**: The `POST /api/v1/rules/preview` endpoint allows managers to test patterns against sample text (up to 10,000 characters). Preview returns match coordinates (`start`, `end`) and match counts. It **never** returns or logs the raw matched text.

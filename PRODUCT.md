# PII Guard

Company employees use a plain chat interface to submit text and files to an LLM through a privacy guard. Managers create employee accounts in their own workspace, assign immediate managers, and configure company identity. Safe reporting and company rules are implemented and connected in PR 18; network enforcement is a roadmap capability, not implemented.

The primary tasks are signing in, adding an employee who can sign in to the same workspace, composing a message, attaching a file or selecting fictional test data, and reading the response. Employee credentials are shared by the manager directly; no invitation email service is configured. Public signup creates a separate company and manager account.

Use local email/password authentication, existing sessions/CSRF, company scoping, and manager assignments. Preserve unrestricted email/password strings and password hashing. Privacy processing that is absent must block actual submissions; local demo adapters remain explicitly development-only. PR 18 adds real OCR/face/text detection with irreversible image/document redaction and safe manager reporting.

The interface uses only black, white and neutral grays, an arrow icon for Send with other controls text-based, both light and dark modes, system typography, restrained spring-like transitions, and accessible reduced-motion behavior. Network/UI claims must describe the real implementation.

# scripts

Feature-owned setup helpers such as seed-demo.sh. Additional platform automation is deferred; document ordinary startup commands first.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `dev.sh` | Deferred | Optional future work; outside the five current issues. Start the documented development stack. |
| `seed-demo.sh` | Existing | Migrate and seed the synthetic demo environment. Owner: [issue 3](../docs/issues/03-auth-company-setup.md). |
| `export-api-schema.sh` | Deferred | Optional future work; outside the five current issues. Regenerate and check contract snapshots. |
| `provision-models.py` | Deferred | Optional future work; outside the five current issues. Acquire licensed models with checksum validation outside Git. |
| `verify.sh` | Deferred | Optional future work; outside the five current issues. Run relevant frontend, backend, engine, and integration checks. |
| `provision-company.py` | Existing | Trusted operator mapping of real WorkOS users and active memberships to company roles. Owner: [issue 3](../docs/issues/03-auth-company-setup.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/anubhav20ch/PII-Project/issues/3)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

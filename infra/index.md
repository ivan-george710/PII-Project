# infra

Reserved for optional future infrastructure. The current app uses the existing root Vercel configuration and GitHub Actions; Compose is deferred.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `compose.yaml` | Deferred | Optional future work; outside the five current issues. Connect web, API, database, storage, and development configuration. |

## Subdirectories

- [deploy/](deploy/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

See the [five approved issues](../docs/issues/index.md). This directory has no required implementation files in the current scope; deferred entries remain optional.

## Network roadmap

`network/` is planned for a separately hosted Linux privacy gateway, firewall and enrollment configuration. Exact files: `compose.yaml`, `nftables.conf`, `.env.example`, and indexes. See [issue #14](../docs/issues/06-network-enforcement.md). This does not change Vercel app deployment or implement network routing yet.

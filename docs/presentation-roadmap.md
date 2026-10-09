# Required presentation content: network protection roadmap

Status: Presentation source notes only. These capabilities are **planned / not implemented**. Do not describe them as a working demo or shipped product. Existing Cadence organizational PPT is reference input, not the project presentation.

## Slide: Company-network enforcement — planned

- Employees use their normal LLM or website; covered traffic passes through a company privacy gateway.
- Managed devices trust the company inspection certificate and authenticate to the gateway.
- Company firewall denies direct egress around the gateway on the protected network.
- Identity maps each enrolled device to the employee and their immediate manager.

Speaker note: Wi-Fi alone cannot inspect encrypted HTTPS. Protection requires configured routing/firewall and enrolled devices. Cellular/hotspots/off-network devices are outside this network-only scope. Uninspectable/unsupported submissions are blocked. Do not say "impossible to bypass on any network".

## Slide: Upload redaction and manager reporting — planned

- Inspect messages and uploads to supported LLM and non-LLM websites before sending.
- Apply company toggles/custom rules to text and files, including planned embedded scan/image/face coverage.
- Forward verified sanitized content; block unsupported uploads or failed inspection.
- Show safe PII categories/counts, employee, destination and action in the immediate manager's account.

Speaker note: No raw PII or original uploads in manager reports. Image/face implementation remains paused/pending. Website compatibility needs verified protocol adapters; do not promise transparent rewriting on every website. Distinguish redaction outcome from upstream delivery outcome.

## Slide: Architecture and implementation status

Planned flow: Managed employee device → enforced company gateway → inspection/redaction + durable audit admission → supported external website. Control plane supplies company policy and identity; immediate manager accesses safe reports in the app.

Vercel hosts the web/API control plane. The network gateway runs on company-controlled infrastructure. Network enforcement and external website inspection are roadmap items, not completed capabilities. Explain implemented app features separately and verify current state before presenting.

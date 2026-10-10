**Before starting: refer to the root `index.md` and the `index.md` in every directory you touch. Follow their exact filenames/responsibilities and update the indexes when files change.**

Status: Requested roadmap capability; **not implemented**. This issue includes implementation, integration, setup, synthetic demonstration data and tests. There is no separate testing/demo issue and no prerequisite issue-completion gate.

## Preserve the current app

Fetch current upstream main before starting and before submitting. Preserve local email/password auth, signup, Argon2 hashes, database sessions, CSRF, existing company/employee/manager assignments, monochrome icon-free UI, migrations and passing CI. Do not restore WorkOS. Email/password remain strings without format/verification/strength/length checks. Add migrations after the actual current head; never rewrite applied migrations. Use real implementations in production; explicit synthetic adapters are test/development-only. Missing privacy processing must block outgoing submissions.

Python boundaries use Pydantic v2 (`extra="forbid"`, strict booleans/integers, UUIDs, aware UTC timestamps, bounded lists/strings). Frontend boundaries use strict Zod schemas. Reject unknown fields and malformed data. Use the existing error envelope `{error:{code,message,fields,request_id}}`; messages/fields must not contain raw PII, passwords, tokens, upload bodies, or certificate private keys. Use 401 unauthenticated, 403 unauthorized, 404 unavailable/foreign resource, 409 conflict, 413 limits, 415 unsupported media, 422 validation, 503 unavailable enforcement components. Cookie mutations require existing CSRF and allowed Origin checks. IDs/roles/company membership are resolved from authenticated identities, never trusted from browser-supplied company/employee IDs.

# Enforce company-network egress through an employee-aware privacy gateway

## Outcome and honest boundary

An enrolled employee on the protected company network can use an external LLM website or another website directly without opening our chat app, but covered outbound traffic still traverses the company's privacy gateway. Direct internet access that bypasses that gateway is denied. Deploy the gateway and firewall on a company-controlled Linux host/router; Vercel continues hosting the existing control-plane app and is not a Wi-Fi router or packet proxy.

HTTPS content inspection requires a company-managed device trusting a company inspection CA. Wi-Fi membership alone neither decrypts TLS nor identifies an employee. Unenrolled devices receive no protected-network internet access; any separate guest network must be explicitly outside the protected promise. Off-network cellular/hotspot traffic is outside this network-only scope. Do not promise universal, unbypassable inspection, inspection of arbitrary end-to-end encrypted payloads, or protection for unmanaged/off-network devices. Endpoint/MDM enforcement beyond CA/proxy enrollment is future scope.

## Deliver together

1. A containerized Python/mitmproxy gateway with authenticated explicit HTTP/HTTPS proxying, HTTP CONNECT interception and upstream TLS verification. Forward only traffic released by the inspection contract below. HTTP/1.1 and HTTP/2 are mandatory; pin actual dependency versions and document supported clients.
2. Linux nftables routing/firewall configuration forcing protected clients to the gateway. Include both IPv4 and IPv6. Either implement IPv6 rules or disable IPv6 on the protected segment with explicit verification; never leave an IPv6 bypass. Block direct external TCP/UDP egress, external proxies, VPN tunnels and unapproved DNS. Allow only documented infrastructure destinations/services. Restrict QUIC/UDP 443 so supported browsers use inspected TCP; block unsupported transports rather than claiming they were inspected.
3. Device enrollment, revocation and authenticated employee identification without using the destination website's account/cookies. Use an authenticated browser enrollment agent/managed proxy configuration and a per-device credential; do not infer identity from public IP, shared NAT, hostname, MAC address alone or an untrusted header. For the initial managed-browser implementation use a generated per-device proxy credential over a TLS-protected client-to-gateway connection. Strip proxy credentials before forwarding and reject unauthorized CONNECT requests. Document browser/OS support and proxy-auth limitations; unsupported clients are blocked.
4. Company inspection CA generation/distribution instructions for the managed demo devices. Keep private keys only on the gateway in restricted mounted storage. Never return private keys to the browser or commit certificates with private keys. Verify normal upstream TLS errors are not suppressed. Certificate-pinned/mTLS clients that cannot be safely inspected are blocked; no silent CONNECT tunnel exemption.
5. A small manager settings page for gateway status and device enrollment/revocation using the existing app shell, black/white/grayscale, no icons. No new employee chat screen is required.
6. Health/status, bounded timeouts, audited state transitions and restart behavior. A gateway or control-plane outage must not activate a direct-egress fallback.

## Device/control-plane API

Prefix `/api/v1/network`. All public endpoints require existing manager session and company scoping. Managers may enroll only their own currently assigned active employees; do not grant company-wide employee visibility just because a user has the manager role. Enrollment is a manual demonstration workflow, not enterprise MDM.

- `POST /devices`: JSON `{employee_id:"<uuid>",label:"Office laptop"}`. `label` trimmed 1..80. Resolve company and the assigned employee server-side. Return 201 `{device:{id,employee_id,label,status:"active",created_at,revoked_at:null},proxy_username:"<device UUID>",proxy_password:"<one-time generated secret>",proxy_url:"https://<configured gateway host>:8443",ca_certificate_url:"<authenticated download URL>"}`. Secret is at least 32 cryptographically random bytes, shown once and never persisted plaintext in the API database/logs. Hash for verification. Gateway registration uses an authenticated service channel; if registration fails return 503 and do not mark enrollment successful. Proxy URL is trusted configuration, never supplied by the browser.
- `GET /devices?limit=25&cursor=...`: return 200 `{items:[device summaries],next_cursor:null}`. Limit 1..100; cursor <=512, opaque/company-scoped. List only caller's assigned employee devices. No credentials in listing/detail responses.
- `DELETE /devices/{device_id}`: idempotent 204 for an authorized device; 404 foreign device. Revoke credential, invalidate cached identity and terminate device connections. Gateway must enforce revocation before returning successful completion, otherwise 503 with a safe error. Persist revocation intent so retries/restarts complete it; do not reactivate on failure.
- `GET /status`: 200 `{gateway_id:"<uuid>",state:"enforcing|unavailable|degraded",last_seen_at:"<UTC or null>",policy_version:<positive integer or null>,protected_network_configured:<boolean>,capabilities:["http1","http2","tls_inspection"]}`. State is not enforcing until gateway heartbeat, identity channel, policy, inspection runtime and administrator-verified routing configuration are all ready. A heartbeat alone does not prove the firewall is correctly deployed.
- `GET /ca-certificate`: download public CA certificate with trusted filename/MIME; manager-authenticated/company-scoped. Never return CA key. CA rotation procedures must cover device re-enrollment and retirement.

Service-to-service requests authenticate a gateway with mTLS against a registered, organization-scoped gateway identity. Use a separate service dependency, never local manager cookies or a universal bearer key passed in client headers. Registered certificate fingerprint/expiry identifies the gateway; request body `organization_id` cannot grant access to another company. Reject expired/revoked certificates. Gateway identity lookup must validate active company, active employee and device revocation before each new request. A gateway identity cache may last at most 30 seconds; no expired cache permits uploads during API outages. Persisted revocation version/ack must invalidate it immediately. Document certificate issuance/rotation/revocation for the demo; keys stay outside source/GitHub issue bodies.

## Shared gateway contract

Implement Pydantic `EmployeeContext`: `{organization_id,employee_id,device_id,gateway_id,authenticated_at,identity_expires_at}`. IDs UUID, timestamps UTC; expires > authenticated and lifetime <=30 seconds. Issued by trusted service code after device verification; the upload addon must not accept an arbitrary context object from HTTP headers. An employee needs a current immediate-manager assignment for outbound submissions; missing/inactive assignment blocks the submission with `MANAGER_UNASSIGNED` and an organization-scoped operational event.

Gateway calls `inspect_outbound(context,request) -> GatewayDecision` from `packages/gateway/src/pii_gateway/contracts.py`. Request exposes validated HTTP method, destination host/port, content type, body spool and request UUID; raw values are private memory/private temporary files. Decision fields: `{request_id,action:"forward|block",body_path:<private sanitized spool or null>,headers:<validated rewritten headers>,event_receipt_id:<uuid or null>,reason_code:<safe code or null>}`. `forward` requires a complete inspection decision and a durable audit receipt for submissions; original body must never be chosen as fallback. Full parsing/rewrite/report implementation belongs to the upload capability, but this workstream must include the integration and deny any submission while that real capability is unavailable. Do not add a fake production sanitizer or return clean merely because an addon is missing.

The gateway itself may stream ordinary download responses after policy-approved request classification. Never stream an outbound submission body to its destination before inspection. Do not capture destination credentials, login/password fields or unrelated browsing content for manager reports. Login/auth traffic uses an explicit tested classification, not a blanket exemption for arbitrary POST requests. Unclassified body-bearing traffic is blocked until a safe classifier/adapter exists.

## Configuration and deployment

Deliver `infra/network/compose.yaml` for a dedicated Linux gateway/demo host, gateway TLS listener 8443, restricted control-plane mTLS channel and persistent encrypted/private spooling volume. Deploy network appliance separately from Vercel. Required placeholder settings: `GATEWAY_ID`, `CONTROL_PLANE_URL`, `GATEWAY_CLIENT_CERT_PATH`, `GATEWAY_CLIENT_KEY_PATH`, `CONTROL_PLANE_CA_PATH`, `INSPECTION_CA_CERT_PATH`, `INSPECTION_CA_KEY_PATH`, `PROTECTED_INTERFACE`, `UPLINK_INTERFACE`, `PROTECTED_CIDR_V4`, optional `PROTECTED_CIDR_V6`. Validate interface/CIDR configuration. Secrets use mounted restricted files/SecretStr, never browser environment variables.

Provide setup/preflight/rollback commands. Validate firewall syntax before activation, preserve an explicit administrator management route, and document what rules change. Do not run firewall mutations on a developer's workstation or an existing office router without a deliberate deployment action. Health checks need not create a second release platform. Do not weaken existing Actions tests/deployment checks; gateway container checks are separate checks in the same workflow.

## Acceptance and failure cases (part of this issue)

- A managed browser accesses a synthetic HTTPS LLM endpoint and a synthetic HTTPS non-LLM upload endpoint through the gateway without using our app; employee/device identity is correct.
- Direct IPv4 and IPv6 access, proxy removal, alternate DNS, UDP 443/QUIC, a test VPN and a test external proxy cannot send data to an instrumented external receiver on the protected segment. Document exactly which bypass classes were tested; do not imply this proves all possible tunnels.
- No CA installed, pinned TLS, invalid upstream certificate, unknown/revoked device, spoofed employee headers and unknown protocols cannot transmit a protected submission. Destination sees zero body bytes when blocked.
- Shared NAT/two employees/two managers preserve distinct identity; cross-company devices and manager device operations are denied.
- API/gateway restart, unavailable inspector, stale identity and incomplete policy cause blocked submissions; no fail-open tunnel.
- Revocation cancels current connections and rejects new ones; replaying old credentials fails.
- Explain the off-network/cellular boundary, managed-device prerequisite and what traffic is classified as exempt. Present UI status honestly.
- Tests/fixtures and a two-employee/two-manager demo setup ship here; no separate testing ticket. Actual engine unavailable means demonstration is labeled simulated and production remains blocked.

## Exact file ownership

All new executable files below are planned. Create/update `index.md` at each new directory level when implementing.

| File | Responsibility |
|---|---|
| `packages/gateway/pyproject.toml` | Gateway package, pinned proxy dependencies, Python version and checks. |
| `packages/gateway/src/pii_gateway/__init__.py` | Package exports. |
| `packages/gateway/src/pii_gateway/config.py` | Strict settings and secrets/file paths. |
| `packages/gateway/src/pii_gateway/contracts.py` | Shared employee/request/decision models; preserve contracts for upload integration. |
| `packages/gateway/src/pii_gateway/main.py` | Start TLS-protected proxy and required addons; absent required addon is fatal. |
| `packages/gateway/src/pii_gateway/identity.py` | Credential verification, device context, revocation and bounded identity cache. |
| `packages/gateway/src/pii_gateway/control_plane.py` | mTLS control-plane client and policy/heartbeat integration. |
| `packages/gateway/src/pii_gateway/tls.py` | CA/certificate lifecycle, interception and verified upstream TLS. |
| `packages/gateway/tests/test_network_enforcement.py` | Protected-segment routing/bypass acceptance with instrumented receiver. |
| `packages/gateway/tests/test_identity.py` | Device identity, two employees, revoked credentials and cache expiry. |
| `apps/api/app/routes/network.py` | Public device/status/certificate endpoints and authenticated service control plane. |
| `apps/api/app/schemas/network.py` | Device/status/employee-context boundary DTOs. |
| `apps/api/app/services/network.py` | Enrollment/revocation, safe service identity resolution and status. |
| `apps/api/app/db/models/network_device.py` | Device credential hash, employee/company ownership, status and revocation version. |
| `apps/api/app/db/models/network_gateway.py` | Registered service identity/certificate fingerprint/heartbeat. |
| `apps/api/migrations/versions/<next_unique_revision>_network_identity.py` | Add gateway/device tables after actual head; retain existing user/assignment tables. |
| `apps/api/tests/test_network.py` | API authorization, mTLS identity, enrollment and revocation cases. |
| `apps/web/src/features/network/NetworkSettings.tsx` | Simple manager enrollment/status UI. |
| `apps/web/src/features/network/schemas.ts` | Strict Zod network forms/responses. |
| `infra/network/compose.yaml` | Dedicated gateway Linux-host deployment. |
| `infra/network/nftables.conf` | Documented protected-network IPv4/IPv6 egress enforcement rules. |
| `infra/network/.env.example` | Only placeholder configuration used by this capability. |
| `docs/network-enforcement.md` | Setup, trust/identity, verification, rollback, coverage and limitations. |

## Official technical references

HTTPS interception/trust and pinned-client limitations: [mitmproxy certificates](https://docs.mitmproxy.org/stable/concepts/certificates/) and [ignoring domains](https://docs.mitmproxy.org/stable/howto/ignore-domains/). Modes and protocol behavior: [proxy modes](https://docs.mitmproxy.org/stable/concepts/modes/) and [protocol support](https://docs.mitmproxy.org/stable/concepts/protocols/). Confirm actual chosen version behavior when implementing; these references are not evidence that this repo has already delivered the feature.

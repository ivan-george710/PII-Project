# Employee chat walkthrough

1. Sign in as an employee using the local email/password account and open Chat.
2. Use the composer `+` menu to select fictional message examples or synthetic files. Message examples only populate the draft; file examples become normal employee-owned uploads.
3. Submit the draft and attachments. The configured company policy, real privacy engine, and reporting sink process the request before any LLM provider receives sanitized content.
4. Review the sanitized message and streamed response. A failed guard/report/storage stage blocks the provider call.
5. Sign in as an authorized manager in the separately delivered manager views to verify company-scoped events and policy changes.

The deterministic LLM adapter requires `APP_ENV=development` or `test` and `DEMO_ADAPTERS_ENABLED=true`; never enable simulated adapters in production. The sample catalog uses the independent `SHOW_DEMO_SAMPLES=true` setting. `faces.jpg` is deliberately not distributed because no licensed source asset is available; do not replace it with an unlicensed image.

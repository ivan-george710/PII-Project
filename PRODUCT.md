# PII Guard

<!-- impeccable:product-schema 1 -->

## Platform

Web application with a local employee processor and a remote manager page.

## Users and purpose

Employees submit text and supported documents through a simple chat. The pseudofix engine extracts, detects, redacts, verifies and retains its review evidence. No LLM is used. One static manager sees submitted filenames, times and affected content, and approves or denies the redacted download. There is no authentication or multi-account setup in this demonstration.

## Required boundaries

Preserve the teammate engine and its verification/review rules. Approval cannot override processing failure, unsupported content, unresolved findings or failed verification. Only manager reports and decisions cross to the existing Vercel service; full employee input, files and processing remain local. Only the affected portions belong in manager comparisons. Download approval is revision specific; changing findings or regenerating an artifact requires a fresh decision. Failed report sync blocks release.

## Interface requirements

Preserve existing graphs, diagrams, visual evidence and non-text content. Reduce explanatory copy and technical clutter. Use the previously approved rounded diamond-loop SVG and send arrow, a plain chat composer with attachment/test-data controls, monochrome light/dark themes, larger headings, small Strands loading, restrained spring motion and reduced-motion support. The manager page must work comfortably on mobile.

## Scope and evidence

The existing engine capabilities and limitations are documented in README.md and the phase reports. Do not claim universal PII, image/document coverage or network interception. Planned manager sync/approval must be verified before marking it implemented.

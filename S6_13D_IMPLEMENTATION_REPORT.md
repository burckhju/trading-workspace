# S6-13d Implementation Report — Request URL Diagnostics

## Scope

Diagnostic-only hardening of FT-007 Playwright E2E tests. No backend, domain, API, or frontend production behavior was changed.

## Changes

- Added browser request observation for all URLs containing `trade-plan` in the two remaining failing FT-007 E2E scenarios.
- Each observed request is emitted as `[FT007 request] <METHOD> <URL>` during the Playwright run.
- Added explicit diagnostic messages to the deterministic request-counter assertions so a route-matcher miss points directly to the captured URL lines.
- Existing route mocks, response payloads, and business assertions remain unchanged.

## Goal

Measure the exact browser request URLs for submit-review, detail read, and version-history read. Use those measured URLs in S6-13e to correct the two remaining route matchers without guessing.

# Sprint 3 – Work Unit 10

## Scope

Technical provider-mapping validation, EODHD account-usage synchronization, and process-local operational metrics.

## Decisions

- Administrative approval and technical provider validation are separate concerns.
- A mapping becomes `ACTIVE` only after an exact EODHD Search API match for symbol and exchange.
- A missing exact match produces `INVALID`; listing master data is never changed.
- The EODHD User API can raise local observed usage but never reduce it.
- User API values are non-secret operational data; the API key and provider URLs remain hidden.
- Metrics remain process-local and therefore do not remove the single-instance restriction.

## Provider endpoints

- Search API: technical symbol/exchange validation.
- User API: `apiRequests`, `apiRequestsDate`, `dailyRateLimit`, and `extraLimit`.

## Tests

- exact technical mapping match,
- invalid technical mapping,
- administrative handling of invalid validation results,
- external account usage synchronization,
- complete backend unit and contract regression.

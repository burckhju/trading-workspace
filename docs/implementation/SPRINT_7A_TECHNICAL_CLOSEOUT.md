# Sprint 7A – FT-002 Technical Closeout

## Status

**RELEASED – SPRINT 7A CLOSED**

FT-002 feature implementation and architecture gap closure are complete. All repository-defined Backend, Frontend and End-to-End CI gates passed on Pull Request #8 before merge into `main`.

## Delivered capability

- existing global provider-neutral `TradingVenue` identity retained;
- MIC canonicalization and uniqueness;
- technical optimistic concurrency for Venue administration;
- activate/deactivate lifecycle preserving historical references;
- global Venue audit using the existing audit infrastructure;
- admin/system service and REST mutations;
- separate admin read contract including inactive venues;
- provider reconciliation integrated into mapping validation;
- read-only reconciliation visibility for conflict diagnosis;
- low-input Underlying/Listing behavior;
- exceptional admin UI outside the primary trader navigation;
- FT-004 consumer compatibility contract without Warrant implementation.

## User impact

TradingVenue is deliberately not a recurring trader input. If one valid venue exists, it is used automatically. A venue selection is requested only when multiple valid venues make the choice materially relevant. Provider ambiguity/conflict is handled through reconciliation and administration rather than free-form technical input by the trader.

## Verified evidence in the available environment

### Backend functional gate

- 299 unit/integration tests passed.
- Ruff passed.
- Black check passed.
- Coverage: 85.60%, threshold 85%.
- FT-002 migration contract test passed.
- Migration chain is explicitly `20260811_0008` → `20260813_0009`.

The reconstructed local environment could not reproduce the complete Python 3.12 wrapper reliably. The authoritative protected-branch Backend CI on PR #8 subsequently passed, including Ruff, Black, mypy and tests with coverage.

### Frontend gate

Using the installed packages directly because archived executable wrappers lost execute permissions:

- TypeScript typecheck passed.
- ESLint passed.
- Prettier passed.
- 64 frontend tests passed.
- Overall frontend statement/line coverage: 90.13%; branch coverage: 77.13%; function coverage: 81.20%.
- Coverage command passed the repository thresholds (lines/functions/statements 80%, branches 70%).
- Vite production build passed.

### End-to-End

- FT-002 Playwright contract is discovered as two Chromium scenarios.
- Local Chromium execution is blocked before the first test action because the required Playwright Chromium binary is not installed.
- Docker-based repository E2E cannot be executed in the available environment.

## Migration review

Migration `20260813_0009_ft002_trading_venue_persistence.py`:

- extends the existing `trading_venues` table rather than creating a parallel identity;
- canonicalizes existing MIC values;
- initializes technical Venue version to 1;
- adds MIC-uppercase and positive-version constraints;
- enables global reference audit events by making `audit_events.workspace_id` nullable;
- does not introduce provider exchange code, Issuer, Warrant or Currency ownership into TradingVenue.

The migration contract `0008 → 0009` is covered by automated tests; PR #8 passed the repository End-to-End CI gate.

## Final release evidence

FT-002 passed all protected-branch CI gates on Pull Request #8:

- Backend: PASS
- Frontend: PASS
- End-to-End: PASS

Pull Request #8 was merged into `main`.

Merge commit: `7f39bc0`.

Sprint 7A / FT-002 is released and technically closed.

## Decision

No additional FT-002 product functionality is required before release. Failures in the remaining gates should be treated as targeted release-gap fixes, not as justification to expand feature scope.

FT-003 Issuers starts only after S7A closeout/release unless an explicit planning decision changes that sequence.

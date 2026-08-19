# Sprint 11 – FT-011 Backend Acceptance Matrix

## Status

PASS – Backend acceptance qualified.

Qualification baseline:

- 35 / 35 AT-S11 acceptance contracts accounted for
- 107 FT-011 unit tests PASS
- 11 FT-011 PostgreSQL integration tests PASS
- complete backend gate PASS
- 633 total backend tests PASS
- Ruff PASS
- Black PASS
- MyPy PASS
- coverage 86.47% >= required 85%
- PostgreSQL test isolation verified
- Alembic head: 20260818_0019

## Acceptance Matrix

| AT | Requirement | Primary Evidence | Status |
|---|---|---|---|
| AT-S11-001 | Observation only after Full Exit | `test_start_requires_full_exit` | PASS |
| AT-S11-002 | Full Exit permits ACTIVE Observation, target 20 | `test_start_pins_listing_and_persists_observation`; full lifecycle PostgreSQL test | PASS |
| AT-S11-003 | Second start creates no duplicate | `test_start_rejects_existing_observation`; PostgreSQL unique constraint test | PASS |
| AT-S11-004 | Same-Day-EOD excluded | `test_same_day_eod_is_excluded` | PASS |
| AT-S11-005 | Pinned listing remains stable | `test_refresh_uses_pinned_listing` | PASS |
| AT-S11-006 | Ambiguous listing fails deterministically | `test_listing_resolver_rejects_multiple_active_primary_listings`; listing-resolution error mapping | PASS |
| AT-S11-007 | Only real available DailyPrice observations count | `test_missing_dates_are_not_synthesized`; `test_refresh_keeps_active_before_twenty_points` | PASS |
| AT-S11-008 | Completion at 20 observations | `test_refresh_completes_at_twenty_points`; PostgreSQL lifecycle test | PASS |
| AT-S11-009 | Highest High | `test_highest_high_and_date_are_reported` | PASS |
| AT-S11-010 | Lowest Low | `test_lowest_low_and_date_are_reported` | PASS |
| AT-S11-011 | Final Close | `test_final_close_is_last_selected_point` | PASS |
| AT-S11-012 | Target Crossing from DailyPrice.high | `test_target_crossing_uses_daily_high`; `test_uncrossed_target_remains_false` | PASS |
| AT-S11-013 | Stop Crossing from DailyPrice.low | `test_stop_crossing_uses_daily_low` | PASS |
| AT-S11-014 | Plan and management levels remain distinct | planning-context adapter tests + management-event adapter test + separate application contracts | PASS |
| AT-S11-015 | Historical maturity/provenance | `test_product_context_uses_historical_evaluation_and_terms` | PASS |
| AT-S11-016 | Maturity does not truncate Underlying horizon | `test_at_s11_016_maturity_does_not_stop_underlying_horizon` | PASS |
| AT-S11-017 | No post-maturity virtual Warrant P&L | architecture/non-scope contract: observation evidence contains Underlying EOD facts only; no Warrant pricing/settlement/exercise path | PASS |
| AT-S11-018 | Review cannot finalize before completion | `test_draft_requires_completed_observation`; stable `OBSERVATION_HORIZON_NOT_COMPLETE` mapping | PASS |
| AT-S11-019 | Draft editable without new version | `test_update_draft_persists_assessments_without_finalizing` | PASS |
| AT-S11-020 | Four assessments required | domain finalized-review invariant + `ExitReviewIncompleteError` path | PASS |
| AT-S11-021 | Rationale required | `test_at_s11_021_empty_rationale_returns_stable_error_code` | PASS |
| AT-S11-022 | Valid assessment values only | enum + persistence constraints + `test_at_s11_022_and_032_not_assessable_is_valid_final_assessment` | PASS |
| AT-S11-023 | Finalization stores fingerprint and CURRENT | `test_finalize_sets_assessments_and_fingerprint`; PostgreSQL lifecycle test | PASS |
| AT-S11-024 | Finalized review not editable | `test_update_draft_rejects_finalized_version` | PASS |
| AT-S11-025 | Identical inputs remain CURRENT | `test_identical_inputs_remain_current` | PASS |
| AT-S11-026 | Corrected effective input makes review STALE | `test_changed_input_marks_review_stale`; PostgreSQL stale/handoff lifecycle test | PASS |
| AT-S11-027 | Technical/no-semantic refresh remains CURRENT | `test_identical_inputs_remain_current`; deterministic fingerprint tests | PASS |
| AT-S11-028 | New version after staleness supersedes previous | `test_new_draft_supersedes_latest_version` | PASS |
| AT-S11-029 | At most one open Draft | `test_existing_open_draft_is_reused`; `test_database_rejects_second_open_draft` | PASS |
| AT-S11-030 | External Trade without plan remains observable | `test_at_s11_030_external_trade_without_plan_can_start_observation` | PASS |
| AT-S11-031 | Missing provenance is not invented | `test_planning_context_for_external_trade_is_empty`; `test_external_product_context_does_not_invent_terms`; no-stop evidence test | PASS |
| AT-S11-032 | NOT_ASSESSABLE allowed | `test_at_s11_022_and_032_not_assessable_is_valid_final_assessment` | PASS |
| AT-S11-033 | Draft not handoff-ready | `test_handoff_blocks_draft_review` | PASS |
| AT-S11-034 | STALE not handoff-ready | `test_handoff_blocks_stale_review`; PostgreSQL stale lifecycle test | PASS |
| AT-S11-035 | COMPLETED + FINALIZED/CURRENT is handoff-ready | `test_handoff_ready_only_for_completed_finalized_current`; full PostgreSQL lifecycle test | PASS |

## REST Acceptance

Qualified routes:

- `POST /api/v1/post-trade/trades/{trade_id}/observation`
- `GET /api/v1/post-trade/trades/{trade_id}/observation`
- `GET /api/v1/post-trade/trades/{trade_id}/observation/evidence`
- `POST /api/v1/post-trade/trades/{trade_id}/exit-review`
- `GET /api/v1/post-trade/trades/{trade_id}/exit-review`
- `PUT /api/v1/post-trade/trades/{trade_id}/exit-review/draft`
- `POST /api/v1/post-trade/trades/{trade_id}/exit-review/finalize`
- `POST /api/v1/post-trade/trades/{trade_id}/exit-review/revalidate`
- `GET /api/v1/post-trade/trades/{trade_id}/exit-review/history`
- `GET /api/v1/post-trade/trades/{trade_id}/handoff`

Stable error contracts qualified include:

- `POST_TRADE_OBSERVATION_ALREADY_EXISTS`
- `POST_TRADE_NOT_ELIGIBLE`
- `UNDERLYING_LISTING_NOT_RESOLVABLE`
- `POST_TRADE_OBSERVATION_NOT_FOUND`
- `EXIT_REVIEW_NOT_FOUND`
- `OBSERVATION_HORIZON_NOT_COMPLETE`
- `EXIT_REVIEW_INCOMPLETE`
- `EXIT_REVIEW_RATIONALE_REQUIRED`
- `EXIT_REVIEW_NOT_EDITABLE`

## PostgreSQL Qualification

Real PostgreSQL integration verifies:

- FT-011 repository round trips
- observation replacement
- one Observation per Trade
- ExitReview persistence
- ExitReviewVersion persistence
- next-version calculation
- one open Draft constraint
- finalized CURRENT lookup
- UoW commit behavior
- complete Observation -> Review -> Finalize -> Handoff lifecycle
- changed inputs -> STALE -> blocked Handoff
- outer transaction rollback isolation

After integration runs:

- `post_trade_observations = 0`
- `exit_reviews = 0`
- `exit_review_versions = 0`

in the isolated `trading_workspace_test` database.

## Backend Definition of Done

FT-011 backend is accepted for Sprint 11.

No additional backend feature work is required before beginning the
minimal frontend flow defined in
`SPRINT_11_FT011_ACCEPTANCE_AND_FRONTEND_SPEC.md`.

Any later backend change affecting FT-011 must preserve this matrix and
the global backend quality gate.

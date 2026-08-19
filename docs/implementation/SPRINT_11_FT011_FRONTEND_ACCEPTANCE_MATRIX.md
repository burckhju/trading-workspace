# Sprint 11 – FT-011 Frontend Acceptance Matrix

## Status

PASS – Frontend acceptance qualified.

Final qualification:

- Sprint-11 runner: 7 PASS / 0 FAIL / 0 SKIP
- Backend gate PASS
- FT-011 backend unit tests PASS
- FT-011 PostgreSQL integration PASS
- PostgreSQL isolation PASS
- Frontend gate PASS
- Backend acceptance matrix 35 / 35 PASS

## Frontend Acceptance Matrix

| FE | Requirement | Primary Evidence | Status |
|---|---|---|---|
| FE-S11-001 | Start-Button only for eligible closed trade | `TradeManagementPage.test.tsx`: closed position shows action; open position does not | PASS |
| FE-S11-002 | Start creates Observation and opens review flow | `TradeManagementPage.test.tsx`: `startObservation` invoked; navigation targets `/post-trade?trade_id=...` | PASS |
| FE-S11-003 | 13/20 displayed correctly | `PostTradeReviewPage.test.tsx`: progress 13/20 | PASS |
| FE-S11-004 | 20/20 shows COMPLETED | `PostTradeReviewPage.test.tsx`: completed observation | PASS |
| FE-S11-005 | Actual and Counterfactual clearly separated | `PostTradeReviewPage.test.tsx`: separate Actual and Underlying-Nachbeobachtung sections | PASS |
| FE-S11-006 | Maturity notice visible | `PostTradeReviewPage.test.tsx`: maturity boundary notice | PASS |
| FE-S11-007 | Draft can be saved and reloaded | `PostTradeReviewPage.test.tsx`: draft load/save including NOT_ASSESSABLE | PASS |
| FE-S11-008 | Incomplete form cannot finalize successfully | `PostTradeReviewPage.test.tsx`: empty rationale disables finalize | PASS |
| FE-S11-009 | Finalized review is read-only | `PostTradeReviewPage.test.tsx`: finalized state removes edit actions | PASS |
| FE-S11-010 | STALE notice and revalidate action visible | `PostTradeReviewPage.test.tsx`: STALE state and revalidation | PASS |
| FE-S11-011 | Historical review version remains visible | `PostTradeReviewPage.test.tsx`: review history renders multiple versions | PASS |
| FE-S11-012 | Backend error codes translated to understandable messages | `errors.test.ts`: stable code translation + fallback | PASS |

## Frontend Scope Delivered

Implemented:

- FT-011 API types
- FT-011 API client
- stable backend error translation
- `/post-trade` route
- PostTradeReviewPage
- Observation progress
- Actual Exit evidence
- Counterfactual Underlying evidence
- Product / Maturity context
- original planning levels
- later management levels
- ExitReview draft editing
- NOT_ASSESSABLE assessment
- finalization
- CURRENT / STALE status
- revalidation
- review history
- FT-012 handoff status
- closed-trade entry from Trade Management

## Final Sprint-11 Definition of Done

Sprint 11 / FT-011 is accepted.

Backend:
- 35 / 35 acceptance contracts PASS

Frontend:
- 12 / 12 acceptance contracts PASS

Overall qualification:
- 7 PASS
- 0 FAIL
- 0 SKIP

No additional FT-011 feature work is required for Sprint 11.

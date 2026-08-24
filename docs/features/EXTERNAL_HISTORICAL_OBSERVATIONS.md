# External Historical Observations

## Status
Approved for Build – Variant A

## Purpose
Import historical third-party trade proposals as `ExternalObservation` evidence without converting them into workspace `Trade` records.

## User workflow
1. User uploads a supported source file.
2. The system parses and validates all rows.
3. Unambiguous rows are prepared automatically.
4. Ambiguous or incomplete rows remain `PENDING` in a review queue.
5. The user resolves only exceptional rows by selecting a mapping, accepting a reduced mapping where allowed, or discarding the row.
6. The user confirms the batch.
7. Accepted rows create or version `ExternalObservation` records with complete import provenance.

## Scope
- reuse released FT-012 `ExternalObservation`, import batch, import row and import issue contracts;
- batch preview with counts for valid, unresolved and invalid rows;
- review queue for unresolved/invalid rows;
- explicit row resolution/discard actions;
- commit only resolved valid rows;
- immutable import provenance and source payload retention;
- duplicate/version decision must be explicit and auditable;
- external observations remain usable as FT-012 learning evidence.

## Non-Scope
- automatic creation of `Trade`, `TradePlan`, `ProductSelection` or execution records;
- automatic lessons, hypotheses or model changes;
- broker integration;
- portfolio synchronization;
- implicit creation of reference-data objects to satisfy an ambiguous import;
- source-specific parser assumptions without real sample data.

## User impact
The normal user sees one import summary and only reviews exceptions. Clean rows require no row-by-row confirmation.

## Acceptance criteria
- a batch exposes totals for valid, unresolved, invalid, accepted and discarded rows;
- a row with unresolved identity cannot be committed silently;
- discarding a row records actor and timestamp;
- accepting a row records the resulting immutable observation version;
- re-importing the same file is detectable by content hash;
- no import path creates a `Trade` unless the existing explicit `execute-as-trade` command is called separately;
- accepted observation versions retain source filename/batch/row provenance indirectly through `import_row_id`.

## Data-source readiness
The generic workflow and review contracts are source-neutral. A Hebeltrader parser is intentionally deferred until representative source files are available; no column names or parsing rules are invented in this specification.

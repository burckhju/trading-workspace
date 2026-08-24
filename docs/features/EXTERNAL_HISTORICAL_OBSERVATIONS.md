# External Historical Observations

## Status
Approved for Build – Variant A, Bulk Upload

## Purpose
Import historical third-party trade proposals as `ExternalObservation` evidence without converting them into workspace `Trade` records. The primary workflow is bulk ingestion of more than 100 PDF issues in one user action.

## User workflow
1. User selects or drops 100+ supported PDF files at once.
2. The system creates one multi-file import job and fingerprints every file.
3. Files already imported with the same content hash are identified before extraction and are not duplicated silently.
4. Each PDF is parsed independently; extracted recommendation records become staged import rows.
5. Unambiguous records are prepared automatically.
6. Ambiguous or incomplete records remain `PENDING` in an exception-only review queue.
7. The user resolves only exceptional records by selecting a mapping, accepting a reduced mapping where allowed, or discarding the record.
8. The user confirms the import job.
9. Accepted rows create or version `ExternalObservation` records with complete file and row provenance.

## Bulk-processing requirements
- one user action must support at least 100 PDFs and must not require sequential file-by-file confirmation;
- processing is isolated per file so one malformed PDF does not fail the complete upload;
- the UI exposes aggregate progress: files queued, parsed, failed, duplicate; records valid, unresolved, invalid, accepted, discarded;
- extraction results are persisted incrementally so a browser refresh or partial processing failure does not require restarting successful files;
- duplicate detection operates per file content hash and must surface duplicates in the summary;
- a user can retry only failed files;
- the review queue is across the whole import job, with filters by file and issue;
- clean files with no exceptions require no manual review;
- file-level errors preserve filename and a machine-readable failure reason;
- processing order must not affect resulting identities or versions.

## Relevant data from Hebeltrader PDFs
The first inspected sample, issue `#122/2026` dated `10.07.2026`, contains a recommendation for Kinder Morgan with a Call warrant. The source visibly exposes fields suitable for structured extraction, including issue date/number, underlying name and WKN, derivative type and WKN, indicated derivative price and timestamp, targets/stops, strike, omega/leverage and maturity. It also exposes underlying price, underlying targets/stops, GD50/GD200, risk/potential figures and market-context statistics. The article prose and charts remain source context and are not automatically interpreted as model changes.

### Core recommendation record
The first parser slice should target fields that are consistently useful for identity, provenance and later evaluation:
- issue_date
- issue_number
- source_name (`HEBELTRADER`)
- recommendation_title
- underlying_name
- underlying_wkn
- underlying_price
- underlying_currency
- underlying_target_1
- underlying_target_2
- underlying_stop_1
- underlying_stop_2
- derivative_type
- derivative_wkn
- derivative_indicated_price
- derivative_currency
- price_indication_at
- derivative_target_1
- derivative_target_2
- derivative_stop_1
- derivative_stop_2
- strike
- strike_currency
- omega_or_leverage
- maturity_date
- stated_holding_horizon when explicitly present
- stated_upside/risk values when explicitly tabulated
- source_file_name and source_file_hash

Additional page-level market, peer-group and narrative fields may be retained as structured source metadata only after format stability is proven across representative issues.

## Scope
- reuse released FT-012 `ExternalObservation`, import batch, import row and import issue contracts;
- introduce a parent multi-file import job above existing per-file import batches;
- bulk PDF intake and asynchronous/incremental processing semantics;
- Hebeltrader PDF adapter based on inspected real samples;
- batch/job preview with counts for files and extracted records;
- review queue for unresolved/invalid records;
- explicit record resolution/discard actions;
- commit only resolved valid records;
- immutable import provenance and source payload retention;
- duplicate/version decision must be explicit and auditable;
- external observations remain usable as FT-012 learning evidence.

## Non-Scope
- automatic creation of `Trade`, `TradePlan`, `ProductSelection` or execution records;
- automatic lessons, hypotheses or model changes;
- broker integration;
- portfolio synchronization;
- implicit creation of reference-data objects to satisfy an ambiguous import;
- interpreting newsletter prose as a trading rule or model parameter;
- extracting data from unsupported layouts by guessing.

## User impact
The normal user drops a large archive of PDFs once, waits for extraction, and then sees one import summary. The user only handles exceptions. A typical result should look like: `126 files processed · 118 clean · 5 need review · 2 duplicates · 1 failed` followed by the small review queue.

## Acceptance criteria
- a single import job accepts at least 100 PDFs;
- a job exposes file-level and record-level progress and final counts;
- failure of one file does not roll back successfully parsed files;
- clean files require no individual confirmation;
- duplicate files are detected before creating duplicate observations;
- a staged record with unresolved identity cannot be committed silently;
- discarding a record records actor and timestamp;
- accepting a record records the resulting immutable observation version;
- failed files can be retried without reprocessing successful files;
- no import path creates a `Trade` unless the existing explicit `execute-as-trade` command is called separately;
- accepted observation versions retain file/batch/row provenance through import identifiers;
- representative tests include 100+ synthetic/fixture PDFs or equivalent parser fixtures without relying on a single-document happy path.

## Data-source readiness
One real Hebeltrader PDF has now been inspected and is sufficient to establish the initial extraction contract. Before declaring the Hebeltrader adapter stable, a representative sample across multiple dates/layout variants is still required to verify that field positions and labels are sufficiently consistent.

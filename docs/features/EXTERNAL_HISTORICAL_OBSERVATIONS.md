# External Historical Observations

## Status
Implemented – Variant A, Bulk Upload

## Purpose
Import historical third-party trade proposals as `ExternalObservation` evidence without converting them into workspace `Trade` records. The primary workflow is bulk ingestion of 100+ PDF issues in one user action.

## User workflow
1. User selects many supported PDF files at once.
2. The system creates one multi-file import job and fingerprints every file.
3. Files already imported with the same content hash are identified before extraction and are not duplicated silently.
4. Each PDF is parsed independently; extracted recommendation records become staged import rows.
5. Unambiguous records are prepared automatically.
6. Ambiguous or incomplete records remain `PENDING` in an exception-only review queue.
7. The user resolves only exceptional records by selecting existing reference-data mappings or discarding the record.
8. The user confirms the import job.
9. Accepted rows create immutable `ExternalObservation` versions plus `LearningEvidence` with file and row provenance.

## Bulk-processing requirements
- one user action supports at least 100 PDFs without sequential file-by-file confirmation;
- files are processed within the upload request, but each file is persisted independently so a later malformed PDF does not invalidate already processed files;
- the UI exposes aggregate job status and file-level results after processing;
- successful file results are committed incrementally, so later failures do not remove earlier work;
- duplicate detection operates per file content hash and surfaces duplicates in the summary;
- failed files can be added again to the same job for retry;
- the review queue spans the complete import job;
- clean files require no manual review;
- file-level errors preserve filename and a machine-readable failure reason;
- processing order does not affect deterministic WKN identity resolution.

## Relevant data from Hebeltrader PDFs
Representative 2026 samples expose stable labels for issue date/number, underlying name and WKN, derivative type and WKN, indicated derivative price and timestamp, targets/stops, strike, omega/leverage and maturity. They also expose underlying price, underlying targets/stops, GD50/GD200 and risk/potential figures. Article prose and charts remain source context and are not interpreted as model changes.

### Core recommendation record
The implemented parser targets fields useful for identity, provenance and later evaluation:
- issue_date
- issue_number
- recommendation_title
- underlying_name
- underlying_wkn
- underlying_price and currency
- underlying targets/stops
- GD50/GD200
- derivative_type
- derivative_wkn
- derivative_indicated_price and currency
- price_indication_at
- derivative targets/stops
- strike and currency
- omega_or_leverage
- maturity_date
- explicitly tabulated upside/risk values
- source file and content-hash provenance

## Scope
- reuse released FT-012 `ExternalObservation`, import batch, import row and import issue contracts;
- parent multi-file import job above existing per-file import batches;
- bulk PDF intake with per-file persistence;
- Hebeltrader 2026 text-layer parser based on inspected real samples;
- deterministic WKN matching against existing Reference Data;
- job summary and exception-only review queue;
- explicit resolve/discard actions;
- explicit final confirmation before observations are materialized;
- immutable import provenance and source metadata;
- duplicate detection by file content hash;
- accepted observations exposed as FT-012 learning evidence.

## Non-Scope
- automatic creation of `Trade`, `TradePlan`, `ProductSelection` or execution records;
- automatic lessons, hypotheses or model changes;
- broker integration;
- portfolio synchronization;
- implicit creation of reference-data objects to satisfy an ambiguous import;
- interpreting newsletter prose as a trading rule or model parameter;
- guessing unsupported layouts;
- OCR for image-only PDFs in this slice;
- background-worker/job-queue processing in this slice.

## User impact
The user uploads a large archive once, receives one job summary and only handles exceptions. Clean files require no individual confirmation. Duplicate and failed files remain visible and auditable.

## Acceptance criteria
- a single import job accepts 100+ PDFs;
- a job exposes file-level status and final counts;
- failure of one file does not remove successfully processed files;
- clean files require no individual confirmation;
- duplicate files are detected before creating duplicate observations;
- a staged record with unresolved identity cannot be committed silently;
- discarding a record records actor and timestamp;
- accepting a record records the immutable observation version;
- failed files can be retried without reprocessing successful files;
- no import path creates a `Trade` unless the existing explicit `execute-as-trade` command is called separately;
- accepted observation versions retain file/batch/row provenance through import identifiers;
- parser and orchestration tests cover 100+ file contracts and validation/error paths.

## Compatibility note
The parser is validated against representative 2026 Hebeltrader issues. Older-year layouts still require sampling before they are declared supported; unsupported or image-only documents fail explicitly instead of being guessed.

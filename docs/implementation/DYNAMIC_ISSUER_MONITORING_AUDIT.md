# Dynamic issuer monitoring audit

Date: 2026-10-02. Baseline: v1.4.1 / `41d0948da3b6929e13a43c2b33c845790c997bf0`.
Category: operational diagnostic correctness; no domain-policy change.

## Problem and reproduction

The read-only performance audit imported the historical product allowlist from
`audit_issuer_monitoring`. Consequently, a currently scheduled `ISSUER_QUOTES`
job for a newly discovered product was absent from its job counts, positive-bid
evidence and wait condition. With only an unchecked new product, `audit(0)` could
return `wait_completed=true` because it compared zero counted jobs with zero
counted completed jobs. A synthetic HTTP transport reproduces this without a
database, live provider, production identifier or secret.

Separately, `rule_issues` omitted an `INDICATIVE` check carrying `refresh_error`.
Operators therefore had to inspect every rule row or hope it appeared among the
ten slowest requests to find retained-price refresh failures. The compact issuer
job list also did not explain why an `AVAILABLE` job lacked positive-bid evidence.

## Scope and acceptance criteria

1. Include every current `ISSUER_QUOTES` job, independently of static product
   lists; exchange and discovery jobs do not inflate the quote-job count.
2. Count rule checks with an explicit supported issuer provider. If a failed check
   omits its provider, associate it only by the instrument ID of a current issuer
   job. An explicit exchange provider takes precedence over that association.
3. Preserve the existing evidence requirements: available job, supported issuer,
   positive finite Decimal bid, receipt timestamp, no retention and no refresh
   error. This proves neither quote freshness nor execution usability.
4. Show missing positive-bid evidence per product and per job, preserving source
   timestamps, unknown timestamps, retention and errors in compact quote evidence.
5. Include refresh errors in `rule_issues` while retaining their original status.
6. Use only the two existing local runtime-status GETs. No provider call, cycle
   trigger, source selection, database write, notification or trade mutation.

## Implementation and contracts

The change remains in `app.tools.audit_monitoring_performance`. It reuses the
refresh catalogue's supported issuer-provider set and consumes the existing
runtime response fields. It introduces no API, schema migration, model version or
parallel valuation logic. Historical package-specific acceptance tools keep their
explicit target scope; they are not substitutes for current-catalogue diagnostics.

`MONITORING_PERFORMANCE_AUDIT_V1` gains additive evidence fields. Existing job and
success counts now cover the current catalogue. `wait_completed` continues to
mean that the scheduler scan, a completed monitoring cycle and first checks of all
current issuer jobs have been observed; it does not require successful quotes or
prove that both status responses describe one atomic point in time.

## Verification and operational boundary

Synthetic regressions cover new products for both issuers, an unchecked new job,
failed checks without provider metadata, an explicit exchange selection, invalid
or retained quotes, failed jobs and indicative refresh errors. Existing monitoring
concurrency and source-discovery tests remain required. Final SHA and CI results
are recorded in the delivery PR; all existing coverage gates remain in force.

Private operator reports and position identifiers are not repository fixtures.
A checkout hash and `latest` image tag alone do not prove which source is running:
compare container source hashes and Compose provenance before planning an update.
This patch does not establish deployment, provider consent reuse, complete quote
coverage or successful Telegram delivery.

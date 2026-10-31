# Hebeltrader research execution

## Baseline and boundaries

The user-selected research reference remains `Hebeltrader_Regelwerk_v0_3.md`.
SHA-256: `73110ea4842c6d2bf251437f948345dd69627890ed75f0c3aebdc8f090608c49`.
The original document and the 135 private source PDFs remain outside this public repository.
This change does not alter the separate rules/UI work in PR #187, existing TradePlans,
positions, model approvals, orders, production providers or monitoring schedules.

The executable core comparison retains initial published underlying stops and targets,
the pre-Z1 losing-position check after 20 sessions, a once-only 25% Z1 realization,
underlying break-even and the maximum of the prior stop, HH20 minus 3 ATR14,
SMA20 minus 0.5 ATR14, and a confirmed swing low minus 0.5 ATR14.
After Z2, the reference core retains peak protection rather than a mandatory final sale.
These are research assumptions, not a declaration that the full reference or its scores
are implemented, optimal, or approved for live use. The source-near 50/50 scenario and
other existing variants remain separate comparators. Normal long stops cannot loosen;
unit rescaling for corporate actions is a distinct operation.

## Executable acquisition, not another backtest claim

`scripts/research/collect_public_history.py` fetches public daily chart payloads and
ECB exchange-rate history in a bounded read-only process. The ticker input contains
only public listing identifiers, not recommendation dates, entries, stops, targets,
PDF text or personal trades. No API keys, .env files or private data are passed to CI.
The isolated workflow uses read-only repository permission and no stored secrets.
It has no schedule or deployment step. It runs for this research branch's pull request;
a manually requested run is also available after the workflow is on the default branch.

```bash
python -m unittest discover -s scripts/research -p 'test_*.py' -v
python scripts/research/collect_public_history.py \
  --symbols scripts/research/public_symbols.json \
  --start 2024-10-01 --end 2026-09-11 --output research-data
```

Successful payloads are saved byte-for-byte with URL, retrieval time, SHA-256 and
schema summaries. Matching saved responses are reused on rerun. Authentication or
permission denials are not bypassed. Bounded retries respect Retry-After; three
consecutive provider errors defer remaining requests for that run.
Exit 2 means incomplete acquisition. The artifact is returned even on partial failure.
Current artifact retention is three days; preserve an authorized local copy for research.
A historical fetch alone is not a verified instrument identity or complete study.

## Local/private follow-through

Import the returned raw artifact into the existing v0.6 research package; keep all
135 source occurrences in the quality/status matrix. Validate actual session coverage,
price anchors, listing/currency/scale and corporate actions before computing or ranking.
Yahoo OHLC price adjustment, missing dividend payment dates and unsupported corporate
actions require explicit handling. The public collector never sets those review flags.
Preserve published values separately from evidence-supported reconstructions.

Use equal reserved EUR budgets, same entry/execution assumptions and the same cutoff
for all comparable variants. Realized cashflows and open valuation must be separated;
missing histories are neither zero returns nor losses. Underlying results are not
warrant returns. No full-universe winner may be claimed from partial acquisition.

The existing FT-013 governance remains authoritative: evidence and immutable research
versions do not imply runtime activation. A later strategy change requires an explicit
reviewed proposal, not automatic adoption of the best retrospective result.

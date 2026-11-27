# gettex delayed pre-trade schema probe

## Current implementation boundary — 27 November 2026

The checklist below records the original discovery requirements. It is not an
instruction to build a second adapter. Main
`eb7f89a30a1772f2c140c5a11cdfb0284d80fc3c` already contains the
[gettex parser](../backend/app/providers/gettex_delayed/parser.py),
[adapter](../backend/app/providers/gettex_delayed/adapter.py),
[provider configuration](../backend/app/core/config/gettex.py) and the existing
[quote resolver integration](../backend/app/features/position_monitoring/service/quote_runtime.py).
The actual seven-field, headerless schema, MUND/MUNC identities, UTC window,
full gzip validation, per-ISIN failures, shared cache and backoff are covered by
[parser tests](../tests/unit/backend/providers/gettex_delayed/test_parser.py),
[adapter tests](../tests/unit/backend/providers/gettex_delayed/test_gettex_delayed_adapter.py)
and [retention regressions](../tests/unit/backend/features/market_data/test_gettex_retention_regression.py).

The [dated source qualification](reviews/ISSUER_QUOTE_QUALIFICATION_2026-10-30.md)
and [original listing-unit qualification](reviews/GETTEX_LISTING_UNIT_ORIGINALS_2026-11-25.md)
describe their respective evidence and limitations. They do not establish a
fresh quote for a specific current holding. Preserve existing source consent,
listing/mapping and current-unit owners; P01 qualification is a separate task.
Original market status remains unqualified for strict B58. This documentation
does not enable a source, import data or create a mapping.

## Historical discovery checklist

The official gettex delayed pre-trade service publishes gzip-compressed CSV files for MUND and MUNC. Runtime integration must remain fail-closed until the deployment host has verified a real file header and exact instrument-identity fields.

Operational verification should capture, without persisting market data:

1. the latest MUND and MUNC filename;
2. the decompressed CSV header and delimiter;
3. the field carrying ISIN or another stable instrument identifier;
4. bid and ask price fields;
5. currency;
6. observation timestamp and its UTC semantics;
7. whether `DE000VH2LU21` occurs in either feed and under which MIC/listing identity.

Do not enable a parser based on guessed column names. The original adapter,
enum/configuration and delayed-source integration requirements have since been
implemented through the existing `WarrantListingQuoteProvider` owner. Further
work must qualify a concrete source/instrument/use case against those paths;
it must not repeat the historical implementation plan.

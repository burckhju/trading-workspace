# gettex delayed pre-trade schema probe

The official gettex delayed pre-trade service publishes gzip-compressed CSV files for MUND and MUNC. The [extended issuer research](issuer-quote-research-expanded.md) records a complete MUND file probe with three exact `DE000UN37224` matches, seven comma-separated columns and **no header**. MUNC and midnight handling remain unverified. This does not establish coverage for `DE000VH2LU21`.

Runtime integration must remain fail-closed until the deployment host has verified the selected file format and exact instrument-identity fields. Retain previously successful observations with their original timestamps when a refresh fails; see [quote retention](retained-warrant-quotes.md).

Operational verification should record metadata and counts without distributing raw market data:

1. the latest MUND and MUNC filename;
2. whether a CSV header exists, the field count and delimiter;
3. the field carrying ISIN or another stable instrument identifier;
4. bid and ask price fields;
5. currency;
6. observation timestamp and its UTC semantics;
7. whether `DE000VH2LU21` occurs in either feed and under which MIC/listing identity.

Do not enable a parser based on guessed column names. The inspected 538 MB compressed file covers one 15-minute window, not a complete day. Download each new file once centrally, verify complete decompression, filter tracked ISINs, and checkpoint only after a successful scan. Absence from one interval must not erase a previously successful quote.

After the schema is verified, implement the adapter behind `WarrantListingQuoteProvider`, add the provider enum/configuration, and place it in `build_warrant_quote_resolver` as a delayed source. Store accepted observations in the existing durable quote repository instead of introducing a separate history architecture.

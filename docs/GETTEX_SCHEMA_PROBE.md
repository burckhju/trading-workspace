# gettex delayed pre-trade schema probe

The official gettex delayed pre-trade service publishes gzip-compressed CSV files for MUND and MUNC. Runtime integration must remain fail-closed until the deployment host has verified a real file header and exact instrument-identity fields.

Operational verification should capture, without persisting market data:

1. the latest MUND and MUNC filename;
2. the decompressed CSV header and delimiter;
3. the field carrying ISIN or another stable instrument identifier;
4. bid and ask price fields;
5. currency;
6. observation timestamp and its UTC semantics;
7. whether `DE000VH2LU21` occurs in either feed and under which MIC/listing identity.

Do not enable a parser based on guessed column names. After the schema is verified, implement the adapter behind `WarrantListingQuoteProvider`, add the provider enum/configuration, and place it in `build_warrant_quote_resolver` as a delayed source.

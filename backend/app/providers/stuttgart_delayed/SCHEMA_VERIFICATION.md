# Börse Stuttgart XSTU schema verification

The Stuttgart delayed adapter remains fail-closed until one current official XSTU pre-trade payload has been inspected and the configured field mapping has been verified against real records.

## Source boundary

Use only the official Börse Stuttgart XSTU pre-trade download page:

`https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/mifir-ii-delayed-data/xstu-pre-trade/`

Download one recent `XSTU-pretrade-*.json.gz` file from the linked `ddl.service.boerse-stuttgart.de` host. Do not use screenshots, product pages, mirrors, or copied third-party samples for schema verification.

## Structural probe

From the `backend` directory run:

```bash
python -m app.providers.stuttgart_delayed.schema_probe /path/to/XSTU-pretrade-YYYYMMDDTHHMM.json.gz
```

The probe prints only structural metadata: candidate record-array paths, leaf field paths, observed JSON types, and name-based field hints. It intentionally does not print market-data values and does not modify application configuration.

## Verification checklist

Before enabling `market_data.stuttgart_delayed`, verify all of the following against the real payload and at least one known XSTU warrant listing:

- the correct record array path;
- the exact ISIN field and that it identifies the held Warrant, not only the underlying;
- the exact MIC/venue field and an exact `XSTU` value;
- whether bid and ask are represented by a side field or separate price fields;
- the exact price field and numeric units;
- the quotation currency field;
- the observation/publication timestamp field and timezone semantics;
- that best-bid/best-ask aggregation does not combine different instruments or venues.

Only after those checks should the explicit schema mapping be committed and `enabled=true` be considered for deployment. If any field is ambiguous, keep the provider disabled.

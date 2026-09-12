# Warrant strike currency

## Contract

`WarrantTermsVersion.strike_currency_code` identifies the currency of the contractual
strike. It is independent of `WarrantListing.quotation_currency_code`, the currency of
the warrant quote. For example, a strike entered as `500 USD` must remain USD even
when a warrant listing is quoted in EUR. This example is not an automatic product
backfill or a source for an FX rate.

The field is exposed by warrant creation, new terms versions and terms-history
responses. Explicit values are trimmed, uppercased and validated against active
currency reference data. Blank or malformed API values are rejected. `null` (and
an omitted field for older clients) means unknown, never EUR and never the listing
currency. The form sends `null` for an empty entry and displays a warning.

The administration page includes `Strike-Währung` and `Neue Strike-Währung` fields
and displays the currency alongside each historical strike. To correct existing
reference data, create a new terms version with the verified currency and retain
the other verified contractual terms. Historical currency values are not rewritten.
Optimistic concurrency still uses `expected_version` of the warrant.

## Migration

Alembic revision `20260912_0033`, following `20260912_0032`, adds a nullable `varchar(3)`
column with no default, a RESTRICT foreign key to `currencies.code` and a check for
three uppercase characters. Existing rows remain NULL. No user product is selected
by ISIN, no EUR default is assigned and no listing currency is copied.

Downgrading removes the new currency column and therefore loses the newly entered
currency information. Back up before migration or rollback. The integration test
runs upgrade and downgrade in an isolated, transaction-scoped PostgreSQL schema.

## Calculation boundary and scope

The inspected product-selection service calculates bid/ask spreads; the position
valuation service uses warrant bid times quantity. Neither uses strike arithmetic,
so this change deliberately leaves those quote-based calculations unchanged.

The domain method `require_strike_reference_currency()` is an explicit guard for
future currency-based strike comparisons: unknown currency or a different reference
price currency raises an error. Repository conversion preserves the currency. The
guard is not a new pricing engine and does not automatically intercept arbitrary
Decimal arithmetic. No existing strike-comparison call site was changed because the
inspected pricing paths contain none.

Not implemented by this change:

- FX rate retrieval, automatic conversion or settlement/Quanto rules;
- point-denominated strikes or unit conversion (never use `PT` as a fake currency);
- verification or automatic enrichment of individual product terms.

Unknown or point-based terms can still be stored without invented monetary units;
monetary strike comparisons remain unavailable until their proper reference context
is implemented. Valid quote display and quote-based valuation do not depend on a
known strike currency.

## Local deployment

Run in the local repository, after the PR has been merged and with a clean worktree.
Do not source `docker/.env` into the shell or export test database URLs.

```bash
cd ~/Boerse/trading-workspace &&
git switch main &&
git pull --ff-only
```

Take a database backup using the existing deployment's credentials. Then build first,
apply the additive migration with the new image, and start the updated application:

```bash
docker compose --env-file docker/.env -f docker/compose.yml build backend frontend &&
docker compose --env-file docker/.env -f docker/compose.yml \
  run --rm --no-deps backend alembic upgrade head &&
docker compose --env-file docker/.env -f docker/compose.yml up -d
```

The database service must already be running. Verify the deployed revision and schema:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend alembic current

docker compose --env-file docker/.env -f docker/compose.yml exec -T database \
  psql -U trading_workspace -d trading_workspace -c "
select column_name, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
  and table_name = 'warrant_terms_versions'
  and column_name = 'strike_currency_code';"
```

Expected: the column exists, is nullable and has no default. Reload the browser and
check the warrant administration page. Legacy rows should say `Währung ungeklärt`.
Record only a verified currency via a new terms version; verify that its history
shows both old and new values and that the listing quotation currency is unchanged.

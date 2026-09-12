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
currency. The form sends `null` for an empty selection and displays a warning.

The administration page includes `Strike-Währung` and `Neue Strike-Währung` selectors
and displays the currency alongside each historical strike. Both selectors load the
existing `GET /api/v1/market-reference-data/currencies` endpoint, which returns active
references only. They never maintain a separate hardcoded currency list or choose the
first currency automatically. Loading, empty results and request failures have explicit
messages and a reload action. A selected code is retained on failure or deactivation,
not silently changed to EUR or null; native form validation blocks unavailable codes.
The backend remains authoritative and revalidates active references on every write.

To correct existing reference data, create a new terms version with the verified
currency and retain the other verified contractual terms. Historical currency values
are not rewritten. Optimistic concurrency still uses `expected_version` of the warrant.

## Migrations and reference data

Alembic revision `20260912_0033`, following `20260912_0032`, adds a nullable `varchar(3)`
column with no default, a RESTRICT foreign key to `currencies.code` and a check for
three uppercase characters. Existing rows remain NULL. No user product is selected
by ISIN, no EUR default is assigned and no listing currency is copied.

The original `20260803_0001` migration only seeded EUR. Thus a deployment could have
the strike-currency column but reject `USD` with `Strike currency does not exist`.
Revision **`20260912_0034`** permanently closes this reference-data gap for the requested
currencies: USD (US Dollar) and CHF (Swiss Franc), each with minor unit 2. Both are
inserted as active only when absent. `ON CONFLICT (code) DO NOTHING` preserves every
existing field, including local names, reference versions, creation/update timestamps
and intentional deactivations. In particular, a previously added `LOCAL-USD-20260912`
row remains unchanged. EUR and all warrant terms/listings remain unchanged too.

`TW-CURRENCIES-20260912` is the application's seed version, not an ISO publication date.
The supported subset is intentionally limited; this is not a live ISO catalog import.
ISO explicitly identifies the US dollar as USD and the Swiss franc as CHF:
https://www.iso.org/iso-4217-currency-codes.html
The maintenance agency and canonical lists are published by SIX:
https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html

Revision 0034 has a **data-preserving downgrade**: it deliberately does not delete
currency references, which may already be used by historical terms or listings.
Downgrade/re-upgrade is therefore idempotent and cannot silently reactivate a currency.
Revision 0033's downgrade, in contrast, drops the strike-currency column and loses its
values. Back up before any migration or rollback. Do not edit already released migrations.

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

## Regression coverage

`test_usd_chf_currency_references.py` creates randomly named disposable PostgreSQL
databases using `TRADING_WORKSPACE_TEST_DATABASE_URL` credentials (CREATE DATABASE
permission required, supplied by CI). It runs the full real migration chain up to 0033,
checks the original EUR-only state, then upgrades to head. Real REST calls exercise
currency listing, USD/CHF warrant creation, unknown legacy terms, new terms versions
and unchanged EUR quotation. Another case preserves all fields of local USD and inactive
CHF rows across upgrade/downgrade/re-upgrade; inactive CHF remains unavailable and is
rejected by the API. No configured application database is migrated or dropped by these tests.

Frontend tests cover both currency selectors, USD/CHF submission, legacy history,
loading/failure/retry, empty references, unavailable selections and aborted requests.

## Local deployment

Run after merge with a clean worktree and the database service already running.
Do not source `docker/.env` into the shell or export test database URLs.

```bash
cd ~/Boerse/trading-workspace &&
git switch main &&
git pull --ff-only
```

Take a backup outside the repository. Scope the restrictive umask to the backup only:

```bash
(
  set -euo pipefail
  umask 077
  mkdir -p "$HOME/trading-workspace-backups"
  backup="$HOME/trading-workspace-backups/before-currency-references-$(date +%Y%m%d-%H%M%S).dump"
  docker compose --env-file docker/.env -f docker/compose.yml \
    exec -T database pg_dump -U trading_workspace -d trading_workspace -Fc > "$backup"
  test -s "$backup"
  printf 'Backup: %s\n' "$backup"
)
```

Build, apply migrations with the new image, then replace the application containers:

```bash
docker compose --env-file docker/.env -f docker/compose.yml build backend frontend &&
docker compose --env-file docker/.env -f docker/compose.yml \
  run --rm --no-deps -T backend python -m alembic upgrade head &&
docker compose --env-file docker/.env -f docker/compose.yml up -d
```

Verify the revision and reference data:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend alembic current

docker compose --env-file docker/.env -f docker/compose.yml exec -T database \
  psql -X -v ON_ERROR_STOP=1 -U trading_workspace -d trading_workspace -c "
select code, name, minor_unit, is_active, reference_version
from public.currencies
where code in ('EUR', 'USD', 'CHF')
order by code;"

curl -fsS http://localhost:8000/api/v1/market-reference-data/currencies | python3 -m json.tool
```

Expected revision for this change: `20260912_0034`. Missing USD and CHF are now present
and active. Existing inactive rows deliberately stay inactive and are absent from the
consumer endpoint; investigate their deactivation rather than bypassing validation.
Reload the browser. Both terms forms should offer the returned active currencies.
An already known strike currency is not silently changed; legacy terms still display
`Währung ungeklärt`. Save only independently verified product conditions as a new terms
version and check the resulting history. No manual SQL insert is required after upgrade.

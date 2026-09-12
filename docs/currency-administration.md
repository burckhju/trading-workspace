# Reviewed currency catalogs and local administration (variants 3 + 5)

## Separation and initial state

`currency_catalog_releases` stores immutable reviewed catalog documents, their unique
version, canonical SHA-256 checksum and import time. A singleton pointer identifies the
currently reviewed catalog. These tables are separate from `currencies`, which remains
the source of locally permitted monetary currencies used by the existing consumer API.

Migration `20260912_0035` creates only the catalog tables. It imports no catalog and
changes no currency, active flag, historical warrant term, listing or price. Existing
EUR/USD/CHF and manually created references remain untouched. No runtime internet
request, currency conversion, provider activation, order or notification is added.

## Bundled reference data

The application ships a deliberately selected **38-currency monetary subset**, not a
complete or continuously updated ISO catalog. `TW-MONETARY-20260912-V1` was prepared
from the official SIX List One XML retrieved on 2026-09-12. That XML declares publication
date **2026-01-01**; retrieval time is not presented as the publication date.

Source:
https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml

Raw XML SHA-256:
`838dfb991648cf36df939edd5fe3811737962b75a32252847d239cedd1e291c9`

Maintenance agency and current/historical lists:
https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html

Included codes:
`AED AUD BHD BRL CAD CHF CLP CNY COP CZK DKK EUR GBP HKD HUF IDR ILS INR JPY KRW KWD MXN MYR NOK NZD OMR PHP PLN QAR RON SAR SEK SGD THB TRY TWD USD ZAR`.

Names, numeric identifiers and currency minor units are read from that source, not
inferred from quotation currency or assumed to be two decimals. A minor unit is not a
market tick size or an instruction to round strikes or quotes. Fund/accounting, precious
metal, test and no-currency units are outside this feature. Points are not currencies.

## Browser workflow

1. Open **Administration · Währungen** (`/currencies-admin`). Existing local references
   are visible even before the first catalog import.
2. Choose **Mitgelieferten Katalog prüfen**, or select an independently reviewed JSON
   file. Inspect version, publication date, scope, source hash and per-code differences.
3. Explicitly confirm source and change review, then choose **Katalog übernehmen**.
   Importing defines the catalog only: it activates nothing and overwrites no local rows.
4. Search a currency and choose **Aktivieren**, then **Freigabe bestätigen**. A missing
   local row is created from the catalog. For an existing local row only the activation
   flag and update timestamp change; local names and reference provenance are retained.
5. Return to a consumer form and use **Währungen neu laden** (or reload the page).
   Both warrant strike selectors use the existing active-currencies API.

Deactivation is separately confirmed. It removes a currency from selection for new
writes but does not remove or rewrite any historical data. Reactivation requires a
current catalog entry. A conflicting local minor unit blocks activation: the operator
must investigate the reference data rather than having it silently overwritten.
A local active currency omitted from a later catalog remains active and visibly outside
the catalog. Omission is not a deactivation command. No currency deletion is exposed.

## Controlled updates without an application rebuild

The import accepts the documented JSON schema, up to 256000 UTF-8 bytes / 250 entries.
The bundled catalog is one starting snapshot, not a hardcoded runtime whitelist.

For future additions, obtain a current official XML file independently and verify it.
The offline builder selects the **full desired monetary subset**, not just new codes:

```bash
# Within an environment with the project's backend dependencies and PYTHONPATH=backend:
python -m app.tools.build_currency_catalog \
  --source /path/to/reviewed-list-one.xml \
  --codes EUR USD CHF GBP JPY CAD \
  --version LOCAL-REVIEWED-V2 > /path/to/currencies-v2.json
```

The six codes here are an example subset, not the recommended replacement for all 38
bundled codes. Reuse the complete desired code list when expanding a previous catalog.
The builder performs no network or database requests, rejects DTD/entities and conflicting
source rows, and derives source metadata and checksum from the actual XML bytes.
Review the JSON, then upload it in the browser or use the import CLI:

```bash
# Read-only preview is the default. No --apply means no catalog or currency writes.
python -m app.tools.import_currency_catalog --file /path/to/currencies-v2.json

# After reviewing the exact preview, provide the returned token and an operator name:
python -m app.tools.import_currency_catalog \
  --file /path/to/currencies-v2.json \
  --apply --reviewed --expected-preview-token TOKEN_FROM_PREVIEW \
  --actor-name "Operator name"
```

Omitting --file uses the bundled snapshot. For container use, mount the reviewed file
read-only and pass its container path; do not copy credentials into the file. A newly
imported catalog version needs no database migration, application restart or image build.
Newly known currencies still need explicit activation. No periodic downloader is installed.

## Validation, provenance and access boundary

JSON schema and checksum validation are **not source authentication**. A file that merely
claims the SIX URL and a SHA-256 hash is not thereby official. Only an operator-reviewed
source should be submitted; the import confirmation explicitly records that review.
The bundled subset was extracted from the source described above. Future independently
supplied catalogs are the operator's responsibility, not automatically certified by the app.

The API revalidates the catalog server-side. It rejects malformed/duplicate keys and
codes, invalid minor units, unsupported special units, future/older source dates and
reuse of a version identifier with different content. Catalog import and status writes
use PostgreSQL transaction locks and state fingerprints. A stale preview or currency
state yields 409; reload/review rather than retrying an outdated write blindly.
Exact repeated import is a no-op. Each actual write and its audit event commit together.

Currency references are global, as in the existing model, not per-workspace preferences.
The new UI follows the application's existing **trusted local-deployment** access model.
`X-Actor-Id` / `X-Actor-Name` identify audit attribution only; they do not authenticate an
administrator. This feature does not add RBAC or make an internet-exposed deployment safe.
The last 100 currency/catalog audit events are shown; older events are retained in the
existing audit table. No audit event is deleted by these operations.

## API

Base: `/api/v1/market-reference-data/currencies`.
Existing `GET /` (without trailing slash in consumer use) still returns active references.

- `GET /admin`: current catalog plus union of local and catalog currencies, eligibility,
  conflicts and opaque state tokens.
- `GET /admin/history`: last 100 currency/catalog audit events.
- `POST /catalog/preview`: `{ "catalog_json": null }` uses bundled; a JSON string uses upload.
- `POST /catalog/import`: same source plus `expected_preview_token` and `reviewed: true`.
- `POST /{code}/activate` or `/deactivate`: `{ "expected_token": "..." }`.

Opaque tokens are generated by the server, not entered as domain data in the browser.
There is no free-text currency creation endpoint. Backend active-currency validation
remains authoritative even if the browser's cached selection has become outdated.

## Deployment and rollback

After merge, with a clean checkout and running local database, take a `pg_dump -Fc`
backup outside the repository with a restrictive file umask. Then:

```bash
cd ~/Boerse/trading-workspace
git switch main && git pull --ff-only && bash scripts/start-linux.sh

docker compose --env-file docker/.env -f docker/compose.yml \
  exec -T backend python -m alembic current
```

The startup script preserves an existing Frankfurt configuration overlay. Migration
`20260912_0035` must be installed before opening this administration page. No manual SQL
seed is required. Import the bundled catalog and enable only desired currencies in UI.
A Stuttgart download warning is separate and must not be treated as catalog failure.

Downgrading 0035 drops catalog metadata, including release history: back up/export before
rollback. It retains local currency rows, original warrant histories and audit events.
Re-upgrade recreates empty catalog metadata; the desired catalog must be imported again.
Do not use `alembic stamp` to bypass migrations and do not delete user database volumes.

## Tests

Unit cases exercise bundle/schema/source validation, unsafe input and both CLIs.
Disposable PostgreSQL cases run real migrations, preview/import, first activation,
reactivation/deactivation, immutable terms, stale states, version conflicts, simultaneous
requests and atomic rollback when audit storage fails. Existing USD/CHF preservation
regressions remain unchanged. Frontend tests cover reviewed preview, upload errors,
confirmation/cancellation, filtering, missing references and reload after errors.
The real-browser E2E case requires `CURRENCY_E2E_WRITES_ALLOWED=1` and is run only in the
explicitly disposable CI stack; never enable that test flag against a user database.

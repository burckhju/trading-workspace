# ADR-S7-004 – Warrant and WarrantListing Boundary

## Status
Accepted for Sprint 7C after S7C-00 review.

## Decision
Warrant product identity and tradable quotation are separate concepts.

`Warrant 1 -> n WarrantListing`. A WarrantListing references the released FT-002 `trading_venue_id` and owns venue-specific symbols and quotation currency. `trading_venue_id` is not stored directly on Warrant.

ProviderInstrument and MarketDataSeries remain separate from both Warrant and WarrantListing. Existing FT-001 ProviderInstrumentMapping is not silently widened because its current contract is Listing-specific.

## Consequences
The same product can be represented at more than one venue without cloning the product. Execution can later reference a concrete WarrantListing while FT-008 can reason about product identity and tradability separately.

## User impact
The UI must distinguish product data from tradable listings. Users do not need to create a duplicate warrant merely because it is available at another venue.

## Implementation note: optional venue symbol
The existing nullable-symbol contract (migration `20260912_0032`) also applies to the administration UI. When a venue publishes no symbol, leave the Symbol field empty; the API client sends `null`, not an empty string or a substituted ISIN/WKN/underlying ticker. A verified venue and quotation currency remain required. The existing service validates active references and rejects duplicate symbol-less listings for the same product and venue.

A saved product without a listing is still not a ProductSelection candidate. Complete the existing listing form deliberately, then start a new evaluation through the existing product-selection page. Historical runs are not rewritten. Missing quotes remain incomplete data requiring the existing explicit selection confirmation; adding a listing never records a purchase.

Read-only local check after update: open the existing Optionsscheine administration, select a product, and check that Symbol is optional while Handelsplatz and Handelswährung remain required. Do not submit merely for diagnosis. The automated disposable-stack regression is `tests/e2e/warrant-listing-without-symbol.spec.ts` and follows actual listing persistence through the existing confirmation and BUY flow. Never enable its write-test flag on a user depot.

## Implementation note: recover from a blocked selection in the existing flow

`NO_LISTING` is a missing reference-data context, not a missing quote. The existing
Product Selection page now names that reason and links **Notierung ergänzen** to
the existing `/warrants-admin` route. `NO_EFFECTIVE_TERMS` retains its distinct
reason and links to the same product's existing terms administration. A completely
empty historical run offers **Optionsscheinstammdaten prüfen** for its underlying;
it does not claim that today's catalogue is still empty.

The route resolves `selection_run_id` through the existing saved-run API. A supplied
`warrant_id` must occur in that run; the current warrant must still belong to the
run's exact underlying. Invalid, deleted or mismatched targets stop visibly instead
of opening the first unrelated product. The underlying is resolved individually,
including when it is outside the ordinary first catalogue page. No user-entered
UUID or name-based matching is needed. Unknown product identities are not created.

The administration reuses its existing forms and services. When completing a named
existing product, the creation and deletion sections are not offered. When checking
an empty run, the create form retains the exact underlying and shows only products
from that underlying. The repair context does not default the quotation currency.
The optional symbol remains `null` when unknown; venue and currency still require
verified facts. No copied underlying ticker, invented venue or backdated terms.

**Zurück zur Produktauswahl** returns to the exact original run, including after a
reload or cancellation. After a confirmed reference-data write, the user explicitly
chooses **Produkte neu bewerten**, then the existing rationale/confirmation and
separate actual BUY entry. No evaluation, user selection or purchase is triggered
by navigation. Historical omissions remain immutable. Failed saves keep input;
a successful listing write followed by a failed readback explicitly says that the
write succeeded and must not be blindly repeated. Stale detail requests are aborted.

No new page route, purchase entry, endpoint, schema migration, eligibility override
or provider configuration. This changes the UI handoff, not the economic contract.
It does not repair missing real venue/currency facts or unknown instrument identity.
Real master-data correction requires a verified source and explicit user submission.

Regression evidence: `WarrantSelectionRepair.test.tsx`,
`ProductSelectionPage.repair.test.tsx` and the expanded disposable-stack
`warrant-listing-without-symbol.spec.ts` cover exact context, error paths,
empty-run creation, reload, unchanged historic runs and the existing confirmation
through actual persistence. Local read-only check: open an omitted product, follow
the repair link, verify its identity and return without submitting. Saving a listing
or creating a product is a real master-data write; never use a real purchase as a test.

## Implementation note: create product and first listing in one submission

The product creation form now includes the first product venue, quotation currency
and optional venue symbol. **Optionsschein anlegen** submits those inputs once to
`POST /api/v1/warrants`, using the additive optional `initial_listing` object:

```json
{
  "initial_listing": {
    "trading_venue_id": "<verified venue UUID>",
    "quotation_currency_code": "EUR",
    "symbol": null
  }
}
```

The identity, first terms version and first listing remain separate canonical
objects, but are validated before any is staged and committed in one database
transaction. Listing validation is shared with the existing add-listing service:
active venue/currency, exact product scope, no reused underlying venue/symbol,
and existing uniqueness constraints. A failed combined commit rolls back all
three records. This is not two client-side POSTs with partial persistence.

The ordinary UI requires explicit first-listing inputs; the API still accepts
older clients without `initial_listing` and does not invent a listing for them.
No schema migration or backfill is required. A symbol is still optional and never
substituted with the underlying ticker, ISIN or WKN. Neither quotation currency
nor venue is inferred from the underlying or strike. HTTP success still returns
the existing Warrant response; listings remain readable through their owner API.

After a successful creation, the UI confirms the combined save and offers a
separate **Weiteren Optionsschein anlegen** action. A failed follow-up read is
reported as a display error, not as a failed write: the confirmed identity remains
visible and the user is warned not to recreate it. Double submissions are guarded
synchronously. Server-side requests already sent are not cancelled or rolled back
by leaving a page; no network-ambiguity idempotency guarantee is claimed.

Existing saved listings are reused by new Product Selection runs, including after
reload; no second entry of venue/currency is needed. Additional listings for an
existing product remain a separate explicit command with visibly labelled fields.
The new terms editor is collapsed under **Produktbedingungen ändern**, so its
empty currency warning is not confused with the saved terms. Draft listing input
is reset when selecting a different existing product and is never silently moved
to a different product's creation form.

Previously omitted products are not repaired by guessing: the old creation
contract did not persist venue/currency on the Warrant itself. Without a stored
WarrantListing or other verified product-bound source, past unsaved user input
cannot be reconstructed. This implementation does not assert where any individual
user previously entered their data, and does not alter real master data. Old
selection runs remain immutable; re-evaluation, explicit product selection and
actual BUY capture remain separate actions. No quote-provider, consent, monitoring
or execution policy is changed.

Checks: `test_create_with_listing.py`, `WarrantCreateWithListing.test.tsx`, existing
product/service regressions, and the disposable PostgreSQL browser flow in
`warrant-listing-without-symbol.spec.ts` (desktop and mobile creation, readback,
reload, validation failure without orphan product, and unchanged old selection).

The native PostgreSQL transaction regression is
`tests/integration/backend/database/test_warrant_creation_listing_postgres.py`.
It uses an isolated disposable schema and real asynchronous sessions. A child-table
CHECK failure is injected after the product INSERT; a fresh transaction must see
no product, terms or listing. The successful case must retain all three with their
explicit identities and independent strike/quotation currencies. This complements
the migrated REST/browser tests and never operates on a user installation.

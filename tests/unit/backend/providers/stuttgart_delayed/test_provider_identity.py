from uuid import uuid4

from app.core.config.settings import StuttgartDelayedSettings
from app.providers.stuttgart_delayed.adapter import (
    StuttgartDelayedWarrantQuoteAdapter,
    _ListingIdentity,
)


class _Database:
    pass


def test_quote_reports_the_isin_used_for_provider_matching() -> None:
    adapter = StuttgartDelayedWarrantQuoteAdapter(
        database=_Database(),  # type: ignore[arg-type]
        settings=StuttgartDelayedSettings(
            enabled=True,
            schema_version="xstu-pretrade-flat-2026-09-04",
            records_path="$",
            isin_field="Isin",
            mic_field="VenueOfPublication",
            bid_field="Bid",
            ask_field="Ask",
            currency_field="PriceCurrency",
            observed_at_field="TransactionTime",
        ),
    )
    identity = _ListingIdentity(
        listing_id=uuid4(),
        symbol="LOCAL-LISTING-CODE",
        currency="EUR",
        isin="DE000TEST123",
        mic="XSTU",
    )

    quote = adapter._parse_quote(
        [
            {
                "Isin": "DE000TEST123",
                "VenueOfPublication": "XSTU",
                "Bid": "2.40",
                "Ask": "2.50",
                "PriceCurrency": "EUR",
                "TransactionTime": "2026-09-11T18:30:00Z",
            }
        ],
        identity,
    )

    assert quote is not None
    assert quote.provider_symbol == "DE000TEST123"
    assert quote.provider_symbol != identity.symbol

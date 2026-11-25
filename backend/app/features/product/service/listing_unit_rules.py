"""Reviewed public originals for current MUND/EUR equity-call units only."""

from datetime import UTC, datetime

from app.features.product.domain.listing_unit_evidence import (
    ListingUnitRuleDocumentSpec,
    ListingUnitRuleSet,
)

# The observation clock records completed original review, not legal publication
# or historical effectiveness. It limits the consumer quote event; the separate
# full pretrade original establishes product/listing membership at its own time.
# Public API/CLI callers cannot add pins or substitute synthetic rule packages.
SUPPORTED_RULE_SETS: tuple[ListingUnitRuleSet, ...] = (
    ListingUnitRuleSet(
        version="gettex-mund-eur-equity-call-unit-20261125-v1",
        observed_at=datetime(2026, 11, 25, 5, 7, 22, tzinfo=UTC),
        effective_from=None,
        venue_mic="MUND",
        currency="EUR",
        product_class="CALL_WARRANT_ON_EQUITY",
        documents=(
            ListingUnitRuleDocumentSpec(
                role="EXCHANGE_RULES",
                source_reference="https://www.gettex.de/fileadmin/Regelwerke/261102_Boersenordnung.pdf",
                document_sha256="8cb44437079ca807becd54fc3742c76b26cd0ee32cda724d5b2fc97d8c7315d8",
                media_type="application/pdf",
            ),
            ListingUnitRuleDocumentSpec(
                role="OPEN_MARKET_RULES",
                source_reference=(
                    "https://www.gettex.de/fileadmin/Regelwerke/"
                    "180103_Handelsordnung_Freiverkehr.pdf"
                ),
                document_sha256="b27b0659d8cb9e6fb28ff1ed61311bfe40d1e99d2e4d96b7ef305dda9d8b48fb",
                media_type="application/pdf",
            ),
            ListingUnitRuleDocumentSpec(
                role="EXECUTION_RULES",
                source_reference=(
                    "https://www.gettex.de/fileadmin/user_upload/www.gettex.de/Downloads/Regelwerk/"
                    "250117_Ausfuehrungsbestimmungen.pdf"
                ),
                document_sha256="fb59419ceb252792c924ddaeb850c078d5b64c78a50d27f6ca4ccb25176a26fa",
                media_type="application/pdf",
            ),
            ListingUnitRuleDocumentSpec(
                role="PRODUCT_CLASSIFICATION",
                source_reference=(
                    "https://www.derbsw.de/static/c30a7862c1e493be34b39789823b76d0/"
                    "24_07_11_BSW_Produktklassifizierung_Kurzversion_dt_5923f67334.pdf"
                ),
                document_sha256="5c776afd4194f20786d31f7f7e019bdf98b6171dbd0a8e11904672bad6d9b5b1",
                media_type="application/pdf",
            ),
        ),
    ),
)

"""Synthetic local originals and disposable SQLite; no live source or depot facts."""

import gzip
import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.orm.attributes import set_committed_value
from tests.unit.backend.features.product import test_product_review_evidence_reader as existing
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

from app.core.exceptions import ApplicationError
from app.features.market.persistence.models import CurrencyModel, TradingVenueModel
from app.features.product.domain.listing_unit_evidence import (
    ListingUnitImportCommand,
    ListingUnitRoute,
    ListingUnitRuleDocumentSpec,
    ListingUnitRuleOriginal,
    ListingUnitRuleSet,
    QualifiedGettexListingSource,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.listing_unit_evidence import ListingUnitEvidenceModel
from app.features.product.persistence.models import WarrantListingModel
from app.features.product.service import listing_unit_evidence as owner
from app.features.product.service.listing_unit_sources import (
    ListingUnitSourceError,
    require_stream_qualified,
    source_fingerprint,
    validate_qualified_source,
)

NOW = existing.NOW
FILE_NAME = "pretrade.20261118.15.00.mund.csv.gz"
TARGET = existing.ISIN
ROLES = ("EXCHANGE_RULES", "OPEN_MARKET_RULES", "EXECUTION_RULES", "PRODUCT_CLASSIFICATION")
ROW = f"{TARGET},14:57:00.000000,EUR,1.01,100,1.02,100"


def rule_material(**changes):
    originals = tuple(
        ListingUnitRuleOriginal(
            role,
            f"synthetic-{index}.pdf",
            "application/pdf",
            synthetic_kid_pdf(f"Synthetic reviewed public rule role {role}"),
            NOW - timedelta(days=1),
        )
        for index, role in enumerate(ROLES)
    )
    spec = ListingUnitRuleSet(
        version="synthetic-gettex-unit-v1",
        observed_at=NOW - timedelta(days=1),
        documents=tuple(
            ListingUnitRuleDocumentSpec(
                item.role,
                f"https://example.invalid/synthetic/{index}",
                hashlib.sha256(item.document).hexdigest(),
                item.media_type,
            )
            for index, item in enumerate(originals)
        ),
    )
    return originals, replace(spec, **changes)


def qualified(*, content=None, rules=None, spec=None, target=TARGET):
    originals, default_spec = rule_material()
    content = gzip.compress((ROW + "\n").encode()) if content is None else content
    return owner.qualify_gettex_listing_source(
        source=BytesIO(content),
        file_name=FILE_NAME,
        target_isin=target,
        rules=rules if rules is not None else originals,
        known_at=NOW,
        retrieved_at=NOW - timedelta(minutes=30),
        registry=(spec or default_spec,),
    )


@pytest.mark.parametrize("registered_filenames", [False, True])
def test_production_registry_never_accepts_fixture_bytes_or_impersonated_names(
    registered_filenames,
):
    originals, _ = rule_material()
    assert owner.SUPPORTED_RULE_SETS
    known_at = max(spec.observed_at for spec in owner.SUPPORTED_RULE_SETS) + timedelta(seconds=1)
    if registered_filenames:
        documents = {item.role: item for item in owner.SUPPORTED_RULE_SETS[0].documents}
        originals = tuple(
            replace(item, filename=documents[item.role].source_reference.rsplit("/", 1)[1])
            for item in originals
        )
    with pytest.raises(ListingUnitSourceError, match="LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED"):
        owner.qualify_gettex_listing_source(
            source=BytesIO(b"not even read"),
            file_name=FILE_NAME,
            target_isin=TARGET,
            rules=originals,
            known_at=known_at,
        )


def test_complete_file_selects_latest_exact_original_and_keeps_clocks_separate():
    rows = f"{TARGET},14:46:00.000000,EUR,0.99,100,1.00,100\n{ROW}\n"
    content = gzip.compress(rows.encode())
    source = qualified(content=content)
    assert source.pretrade.original_row == ROW
    assert source.pretrade.file_sha256 == hashlib.sha256(content).hexdigest()
    assert source.pretrade.row_sha256 == hashlib.sha256(ROW.encode()).hexdigest()
    assert source.pretrade.observed_at == datetime(2026, 11, 18, 14, 57, tzinfo=UTC)
    assert source.pretrade.retrieved_at < source.qualified_at
    assert source.pretrade.file_bytes == len(content)
    require_stream_qualified(source)
    later = replace(source, qualified_at=NOW + timedelta(minutes=1))
    assert source_fingerprint(later) == source.fingerprint


def test_corrupt_crc_after_a_valid_target_rejects_the_whole_file():
    content = bytearray(gzip.compress((ROW + "\n").encode()))
    content[-5] ^= 1
    with pytest.raises(ListingUnitSourceError, match="LISTING_UNIT_PRETRADE_INVALID"):
        qualified(content=bytes(content))


@pytest.mark.parametrize(
    "rows,code",
    [
        (f"{TARGET},14:55:00.000000,EUR,-1,100,2,100\n{ROW}\n", "GETTEX_ROW_BID_NOT_POSITIVE"),
        (
            f"{ROW}\n{TARGET},14:57:00.000000,EUR,1.00,100,1.02,100\n",
            "GETTEX_DUPLICATE_TIMESTAMP_CONFLICT",
        ),
        (
            "OTHER00000001,14:57:00.000000,EUR,1,100,2,100\n",
            "LISTING_UNIT_TARGET_NOT_IN_PRETRADE_FILE",
        ),
        (ROW.replace(",EUR,", ",USD,") + "\n", "LISTING_UNIT_TARGET_ROUTE_MISMATCH"),
        (ROW.replace("14:57:", "15:57:") + "\n", "GETTEX_ROW_TIME_OUTSIDE_FILE_WINDOW"),
    ],
)
def test_bad_target_rows_are_not_replaced_with_other_good_rows(rows, code):
    with pytest.raises(ListingUnitSourceError, match=code):
        qualified(content=gzip.compress(rows.encode()))


@pytest.mark.parametrize("change", ["missing", "duplicate", "content", "future", "media"])
def test_all_required_rule_originals_must_match_reviewed_pins(change):
    originals, spec = rule_material()
    if change == "missing":
        originals = originals[:-1]
    elif change == "duplicate":
        originals = (*originals[:-1], originals[0])
    elif change == "content":
        originals = (
            replace(originals[0], document=originals[0].document + b"\nchanged original"),
            *originals[1:],
        )
    elif change == "future":
        originals = (replace(originals[0], retrieved_at=NOW + timedelta(seconds=1)), *originals[1:])
    else:
        originals = (replace(originals[0], media_type="text/html"), *originals[1:])
    with pytest.raises(ListingUnitSourceError):
        qualified(rules=originals, spec=spec)


def test_saved_source_integrity_and_internal_scan_capability_are_distinct():
    source = qualified()
    _, spec = rule_material()
    assert validate_qualified_source(source, known_at=NOW, registry=(spec,)) == spec
    forged = replace(
        source, pretrade=replace(source.pretrade, original_row=ROW.replace("1.01", "9.99"))
    )
    with pytest.raises(ListingUnitSourceError):
        validate_qualified_source(forged, known_at=NOW, registry=(spec,))
    copied = QualifiedGettexListingSource(
        source.rule_set_version,
        source.rule_set_fingerprint,
        source.rule_originals,
        source.pretrade,
        source.qualified_at,
        source.fingerprint,
    )
    with pytest.raises(ListingUnitSourceError, match="LISTING_UNIT_COMPLETE_SOURCE_SCAN_REQUIRED"):
        require_stream_qualified(copied)


@pytest.fixture
def context(tmp_path):
    generator = existing.context.__wrapped__(tmp_path)
    value = next(generator)
    try:
        engine = value.sql.get_bind()
        for model in (
            CurrencyModel,
            TradingVenueModel,
            WarrantListingModel,
            ListingUnitEvidenceModel,
        ):
            model.__table__.create(engine)

        @event.listens_for(value.sql, "loaded_as_persistent")
        def sqlite_utc(_session, row):
            # SQLite loses timestamptz offsets; only this disposable synthetic
            # store restores the UTC values it was explicitly given.
            for column in row.__table__.columns:
                field = getattr(row, column.name)
                if isinstance(field, datetime) and field.tzinfo is None:
                    set_committed_value(row, column.name, field.replace(tzinfo=UTC))

        value.warrant.isin = TARGET
        value.currency = CurrencyModel(
            code="EUR",
            name="Synthetic euro",
            minor_unit=2,
            is_active=True,
            reference_version="synthetic",
            created_at=NOW - timedelta(days=60),
            updated_at=NOW,
        )
        value.venue = TradingVenueModel(
            id=UUID(int=9801),
            mic="MUND",
            name="Synthetic gettex venue",
            country_code="DE",
            timezone="Europe/Berlin",
            is_active=True,
            reference_version="synthetic",
            version=1,
            created_at=NOW - timedelta(days=60),
            updated_at=NOW,
        )
        value.listing = WarrantListingModel(
            id=UUID(int=9802),
            workspace_id=existing.WORKSPACE,
            warrant_id=existing.WARRANT,
            trading_venue_id=value.venue.id,
            symbol=None,
            quotation_currency_code="EUR",
            lifecycle_status=WarrantLifecycle.ACTIVE,
            version=1,
            created_at=NOW - timedelta(days=60),
            updated_at=NOW,
        )
        value.sql.add_all([value.currency, value.venue, value.listing])
        value.sql.commit()
        kid = existing.revision(value, isin=TARGET, unit=None)
        kid.document = synthetic_kid_pdf(
            "Basisinformationsblatt PRODUKT Call Optionsschein bezogen auf eine Aktie "
            f"ISIN {TARGET} Basiswert {existing.UNDERLYING_ISIN} Währung des Produkts: EUR "
            "Referenzstelle: New York Stock Exchange "
            "Bewertungstag Der Ausübungstag bzw. der 15.01.2027"
        )
        kid.document_sha256 = hashlib.sha256(kid.document).hexdigest()
        kid.binding = {**kid.binding, "isin": TARGET}
        value.sql.commit()
        value.kid = kid
        value.route = ListingUnitRoute(value.listing.id, "GETTEX_DELAYED", "MUND", "EUR")
        value.command = ListingUnitImportCommand(
            uuid4(), None, value.route, kid.id, NOW, "Synthetic original review only"
        )
        _, value.spec = rule_material()
        value.source = qualified()
        value.importer = owner.ListingUnitImportService(value.session, registry=(value.spec,))
        value.reader = owner.ListingUnitEvidenceReader(value.session, registry=(value.spec,))
        yield value
    finally:
        generator.close()


async def preview(context):
    return await context.importer.preview(
        workspace_id=existing.WORKSPACE,
        warrant_id=existing.WARRANT,
        command=context.command,
        source=context.source,
        now=NOW,
    )


async def record(context, **changes):
    prepared = await preview(context)
    return await context.importer.record(
        **{
            "workspace_id": existing.WORKSPACE,
            "warrant_id": existing.WARRANT,
            "actor_id": UUID(int=9803),
            "command": context.command,
            "source": context.source,
            "expected_preview_fingerprint": prepared.fingerprint,
            "now": NOW,
            **changes,
        }
    )


async def current(context, **changes):
    return await context.reader.current(
        **{
            "workspace_id": existing.WORKSPACE,
            "warrant_id": existing.WARRANT,
            "route": context.route,
            "known_at": NOW,
            **changes,
        }
    )


@pytest.mark.asyncio
async def test_preview_is_passive_and_apply_reuses_exact_source_without_rewriting_kid(context):
    original = (context.kid.document, context.kid.facts.copy())
    context.session.flush.reset_mock()
    prepared = await preview(context)
    context.session.flush.assert_not_awaited()
    context.session.commit.assert_not_awaited()
    assert prepared.operation_status == "READ_ONLY_PREVIEW"
    result = await record(context)
    read = await current(context, event_at=NOW - timedelta(minutes=5))
    assert read.status == "AVAILABLE" and read.revision_id == result.id
    assert read.quality == "CURRENT_UNIT_HISTORY_ASSUMED"
    assert (context.kid.document, context.kid.facts) == original
    assert read.imported_kid_revision_id == read.current_kid_revision_id == context.kid.id
    assert context.session.commit.await_count == 1
    later = await current(context, known_at=NOW + timedelta(seconds=1))
    assert later.fingerprint == read.fingerprint


@pytest.mark.asyncio
async def test_changed_preview_does_not_write(context):
    prepared = await preview(context)
    context.listing.version += 1
    context.sql.commit()
    with pytest.raises(ApplicationError) as error:
        await context.importer.record(
            workspace_id=existing.WORKSPACE,
            warrant_id=existing.WARRANT,
            actor_id=UUID(int=9803),
            command=context.command,
            source=context.source,
            expected_preview_fingerprint=prepared.fingerprint,
            now=NOW,
        )
    assert error.value.code == "LISTING_UNIT_PREVIEW_CHANGED"
    assert context.session.commit.await_count == 0
    assert context.session.rollback.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("effective", [True, False])
async def test_rule_eligibility_boundary_is_not_the_later_import_clock(context, effective):
    boundary = NOW - timedelta(minutes=2)
    context.spec = replace(
        context.spec,
        effective_from=boundary if effective else None,
        observed_at=NOW - timedelta(days=1) if effective else boundary,
    )
    context.source = qualified(spec=context.spec)
    context.importer = owner.ListingUnitImportService(context.session, registry=(context.spec,))
    context.reader = owner.ListingUnitEvidenceReader(context.session, registry=(context.spec,))
    await record(context)
    before = await current(context, event_at=boundary - timedelta(seconds=1))
    expected = (
        "LISTING_UNIT_RULE_NOT_EFFECTIVE_AT_EVENT"
        if effective
        else "LISTING_UNIT_RULE_NOT_OBSERVED_AT_EVENT"
    )
    assert before.status == "UNSUITABLE" and expected in before.reasons
    assert (await current(context, event_at=boundary)).status == "AVAILABLE"


@pytest.mark.asyncio
async def test_absent_not_known_and_changed_routes_are_distinct(context):
    assert (await current(context)).status == "MISSING"
    await record(context)
    assert (await current(context, known_at=NOW - timedelta(seconds=1))).status == "MISSING"
    context.listing.version += 1
    context.sql.commit()
    report = await current(context)
    assert report.status == "UNSUITABLE"
    assert "LISTING_UNIT_CURRENT_BINDING_MISMATCH" in report.reasons

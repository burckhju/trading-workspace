"""Synthetic source-owner reads; no database writes or provider requests."""

from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.application.hebeltrader_source_reader import (
    HebeltraderSourceReader,
)
from app.features.learning.persistence.bulk_import_models import (
    ExternalObservationImportFileModel,
)
from app.features.learning.persistence.models import (
    ExternalObservationImportBatchModel,
    ExternalObservationImportRowModel,
    ExternalObservationModel,
    ExternalObservationTradeLinkVersionRecordModel,
    ExternalObservationVersionModel,
)
from app.features.trade_position.domain.price_binding import PriceBasis

NOW = datetime(2026, 11, 14, 10, tzinfo=UTC)
SOURCE_TIME = datetime(2026, 8, 3, tzinfo=UTC)


@pytest.fixture
def fixture():
    workspace, product, underlying, actor = uuid4(), uuid4(), uuid4(), uuid4()
    observation_id, version_id, row_id, batch_id, file_id = (uuid4() for _ in range(5))
    payload = {
        "issue_date": "2026-08-03",
        "underlying_price": "100.00",
        "underlying_currency": "USD",
        "underlying_target_1": "110",
        "underlying_target_2": "120",
        "underlying_stop_1": "90",
        "underlying_stop_2": "95",
        "derivative_indicated_price": "2.00",
        "derivative_currency": "EUR",
        "derivative_target_1": "3",
        "derivative_target_2": "4",
        "derivative_stop_1": "1",
        "derivative_stop_2": "1.5",
        "recommendation_title": "Synthetic private title is not exported",
    }
    source = ExternalObservationVersionModel(
        id=version_id,
        external_observation_id=observation_id,
        version=1,
        underlying_id=underlying,
        product_id=product,
        source_name="HEBELTRADER",
        source_type="NEWSLETTER_RECOMMENDATION",
        external_reference="123/2026",
        observed_at=SOURCE_TIME,
        recorded_at=NOW,
        imported_at=NOW,
        recording_method="FILE_IMPORT",
        import_row_id=row_id,
        source_metadata={
            **payload,
            "source_file": {
                "file_id": str(file_id),
                "batch_id": str(batch_id),
                "filename": "synthetic.pdf",
                "content_hash": "a" * 64,
            },
        },
        supersedes_version_id=None,
        created_at=NOW,
        created_by=actor,
    )
    observation = ExternalObservationModel(
        id=observation_id,
        workspace_id=workspace,
        current_version_id=version_id,
        created_at=NOW,
        created_by=actor,
    )
    row = ExternalObservationImportRowModel(
        id=row_id,
        batch_id=batch_id,
        workspace_id=workspace,
        raw_payload=payload,
        source_row_number=1,
        resolved_product_id=product,
        resolved_underlying_id=underlying,
        disposition="ACCEPTED",
        validation_status="VALID",
        accepted_external_observation_version_id=version_id,
        disposed_at=NOW,
        disposed_by=actor,
    )
    batch = ExternalObservationImportBatchModel(
        id=batch_id,
        workspace_id=workspace,
        original_filename="synthetic.pdf",
        content_hash="a" * 64,
    )
    file = ExternalObservationImportFileModel(
        id=file_id,
        workspace_id=workspace,
        import_batch_id=batch_id,
        original_filename="synthetic.pdf",
        content_hash="a" * 64,
        status="COMPLETED",
    )
    session = Mock(spec=AsyncSession)
    session.get = AsyncMock(return_value=source)
    session.scalar = AsyncMock(side_effect=[observation, row, batch, file])
    session.scalars = AsyncMock()
    return {
        "session": session,
        "source": source,
        "observation": observation,
        "row": row,
        "batch": batch,
        "file": file,
        "args": {
            "workspace_id": workspace,
            "source_version_id": version_id,
            "product_id": product,
            "underlying_id": underlying,
        },
    }


async def read(fixture):
    result = await HebeltraderSourceReader(fixture["session"]).read(**fixture["args"])
    fixture["session"].commit.assert_not_called()
    fixture["session"].flush.assert_not_called()
    fixture["session"].add.assert_not_called()
    fixture["session"].add_all.assert_not_called()
    return result


async def test_malformed_historical_import_is_unsuitable_not_a_valid_source(fixture):
    fixture["source"].imported_at = None
    result = await read(fixture)
    assert result.source is None
    assert result.reasons == ("NOT_CONFIRMED_PDF",)
    fixture["session"].scalar.assert_not_awaited()


async def test_confirmed_source_preserves_axes_precision_and_provenance_without_article(
    fixture,
):
    evidence = await read(fixture)
    assert evidence.suitable and evidence.reasons == ()
    source = evidence.source
    assert source is not None
    assert source.underlying.binding.basis is PriceBasis.UNDERLYING
    assert source.underlying.binding.instrument_id == fixture["args"]["underlying_id"]
    assert source.underlying.binding.currency == "USD"
    assert source.underlying.target_1 == Decimal("110")
    assert source.product.binding.basis is PriceBasis.WARRANT
    assert source.product.binding.currency == "EUR"
    assert source.product.reference_price == Decimal("2.00")
    assert source.product.scale == source.underlying.scale == "SOURCE_ORIGINAL"
    assert source.time_precision == "DATE_ONLY"
    assert source.issue_date == date(2026, 8, 3)
    assert source.observed_at == SOURCE_TIME
    assert source.recorded_at == source.imported_at == source.accepted_at == NOW
    assert source.content_hash == "a" * 64
    assert source.file_id == fixture["file"].id
    assert source.batch_id == fixture["batch"].id
    assert source.import_row_id == fixture["row"].id
    assert "Synthetic private title" not in str(asdict(evidence))


async def test_historical_version_is_retained_when_a_new_issue_version_exists(fixture):
    fixture["observation"].current_version_id = uuid4()
    fixture["source"].supersedes_version_id = uuid4()
    evidence = await read(fixture)
    assert evidence.suitable
    assert evidence.source.currentness == "SOURCE_SUPERSEDED"
    assert evidence.source.source_version_id == fixture["args"]["source_version_id"]
    assert evidence.source.supersedes_version_id == fixture["source"].supersedes_version_id
    fixture["session"].get.assert_awaited_once_with(
        ExternalObservationVersionModel, fixture["args"]["source_version_id"]
    )


async def test_missing_version_does_not_fall_back_to_current_or_product(fixture):
    fixture["session"].get.return_value = None
    evidence = await read(fixture)
    assert not evidence.suitable and evidence.reasons == ("NOT_FOUND",)
    fixture["session"].scalar.assert_not_called()


async def test_foreign_workspace_does_not_expose_source_and_query_is_scoped(fixture):
    fixture["session"].scalar.side_effect = [None]
    evidence = await read(fixture)
    assert evidence.source is None and evidence.reasons == ("NOT_FOUND",)
    statement = fixture["session"].scalar.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "external_observations.workspace_id =" in sql
    assert fixture["args"]["workspace_id"] in statement.compile().params.values()


@pytest.mark.parametrize("field", ["product_id", "underlying_id"])
async def test_wrong_instrument_is_not_a_valid_source_even_with_matching_currency(fixture, field):
    setattr(fixture["source"], field, uuid4())
    result = await read(fixture)
    assert result.source is None and result.reasons == ("IDENTITY_MISMATCH",)


@pytest.mark.parametrize(
    "field,value",
    [
        ("disposition", "PENDING"),
        ("disposition", "DISCARDED"),
        ("validation_status", "INVALID"),
        ("accepted_external_observation_version_id", uuid4()),
        ("disposed_at", None),
        ("disposed_by", None),
    ],
)
async def test_unaccepted_or_wrong_accepted_version_is_not_confirmed(fixture, field, value):
    setattr(fixture["row"], field, value)
    assert (await read(fixture)).reasons == ("NOT_CONFIRMED_PDF",)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_name", "OTHER"),
        ("source_type", "OTHER"),
        ("recording_method", "MANUAL"),
    ],
)
async def test_other_source_types_are_not_hebeltrader_pdf_evidence(fixture, field, value):
    setattr(fixture["source"], field, value)
    if field == "recording_method":
        fixture["source"].imported_at = None
        fixture["source"].import_row_id = None
    assert (await read(fixture)).reasons == ("NOT_CONFIRMED_PDF",)


@pytest.mark.parametrize("field", ["resolved_underlying_id", "resolved_product_id"])
async def test_import_row_identity_cannot_disagree_with_pinned_source(fixture, field):
    setattr(fixture["row"], field, uuid4())
    assert (await read(fixture)).reasons == ("IDENTITY_MISMATCH",)


@pytest.mark.parametrize(
    "owner,field,value",
    [
        ("file", "import_batch_id", uuid4()),
        ("file", "status", "PARSED"),
        ("file", "content_hash", "b" * 64),
        ("file", "original_filename", "another.pdf"),
        ("batch", "content_hash", "b" * 64),
    ],
)
async def test_provenance_mismatch_is_visible(fixture, owner, field, value):
    setattr(fixture[owner], field, value)
    assert (await read(fixture)).reasons == ("PROVENANCE_MISMATCH",)


async def test_source_marks_cannot_be_overwritten_after_import_confirmation(fixture):
    fixture["source"].source_metadata["underlying_target_1"] = "9999"
    assert (await read(fixture)).reasons == ("PROVENANCE_MISMATCH",)


async def test_missing_original_mark_cannot_be_supplied_only_by_version_metadata(fixture):
    del fixture["row"].raw_payload["underlying_target_1"]
    assert (await read(fixture)).reasons == ("PROVENANCE_MISMATCH",)


@pytest.mark.parametrize(
    "key,value",
    [
        ("underlying_currency", "usd"),
        ("derivative_currency", "GBp"),
        ("underlying_target_1", "NaN"),
        ("underlying_target_2", "Infinity"),
        ("derivative_stop_1", "0"),
        ("underlying_price", True),
        ("issue_date", "2026-08-03T12:00:00"),
    ],
)
async def test_invalid_currency_amount_or_unknown_publication_time_is_not_qualified(
    fixture, key, value
):
    fixture["source"].source_metadata[key] = value
    fixture["row"].raw_payload[key] = value
    assert (await read(fixture)).reasons == ("INVALID_MARKS",)


@pytest.mark.parametrize("payload", [None, {}, {"source_file": {"file_id": "bad"}}])
async def test_missing_or_malformed_provenance(fixture, payload):
    fixture["source"].source_metadata = payload
    assert (await read(fixture)).reasons == ("PROVENANCE_MISMATCH",)


@pytest.mark.parametrize("count", [0, 1, 2])
async def test_trade_source_reuse_needs_one_explicit_active_historical_pin(fixture, count):
    ids = [uuid4() for _ in range(count)]
    versions = [
        ExternalObservationTradeLinkVersionRecordModel(
            external_observation_version_id=value, version=1, change_reason="INITIAL_LINK"
        )
        for value in ids
    ]
    fixture["session"].scalars.return_value = Mock(all=Mock(return_value=versions))
    trade_id = uuid4()
    result = await HebeltraderSourceReader(fixture["session"]).find_trade_source(
        workspace_id=fixture["args"]["workspace_id"], trade_id=trade_id
    )
    assert result == (ids[0] if count == 1 else None)
    statement = fixture["session"].scalars.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "external_observation_trade_links.workspace_id =" in sql
    assert "external_observations.workspace_id =" in sql
    assert "external_observation_trade_link_versions.trade_id =" in sql
    assert "external_observation_trade_link_versions.status =" in sql
    assert "external_observations.current_version_id" not in sql
    assert "ACTIVE" in statement.compile().params.values()
    assert trade_id in statement.compile().params.values()
    fixture["session"].commit.assert_not_called()


@pytest.mark.parametrize("has_unchanged_link", [False, True])
async def test_refreshed_link_does_not_silently_repin_or_hide_a_competing_source(
    fixture, has_unchanged_link
):
    versions = [
        ExternalObservationTradeLinkVersionRecordModel(
            external_observation_version_id=uuid4(), version=2, change_reason="SOURCE_REVALIDATED"
        )
    ]
    if has_unchanged_link:
        versions.append(
            ExternalObservationTradeLinkVersionRecordModel(
                external_observation_version_id=uuid4(), version=1, change_reason="INITIAL_LINK"
            )
        )
    fixture["session"].scalars.return_value = Mock(all=Mock(return_value=versions))
    assert (
        await HebeltraderSourceReader(fixture["session"]).find_trade_source(
            workspace_id=fixture["args"]["workspace_id"], trade_id=uuid4()
        )
        is None
    )

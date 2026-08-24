from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

import app.features.learning.application.bulk_import_service as service_module
from app.features.learning.application.bulk_import_service import (
    BulkImportError,
    ExternalObservationBulkImportService,
    _json_payload,
    _observed_at,
)
from app.features.learning.application.hebeltrader_parser import (
    HebeltraderParseError,
    HebeltraderRecommendation,
)
from app.features.learning.persistence.bulk_import_models import (
    ExternalObservationImportFileModel,
    ExternalObservationImportJobModel,
)
from app.features.learning.persistence.models import ExternalObservationImportRowModel
from app.features.market.persistence.models import UnderlyingModel
from app.features.product.persistence.models import WarrantModel

NOW = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


def _recommendation() -> HebeltraderRecommendation:
    return HebeltraderRecommendation(
        issue_date=date(2026, 7, 10),
        issue_number=122,
        recommendation_title="KI-Boom trifft Pipeline-Gigant!",
        underlying_name="Kinder Morgan",
        underlying_wkn="A1H6GK",
        underlying_price=Decimal("32.40"),
        underlying_currency="USD",
        underlying_target_1=Decimal("39.00"),
        underlying_target_2=Decimal("47.00"),
        underlying_stop_1=Decimal("30.00"),
        underlying_stop_2=Decimal("32.40"),
        gd50=Decimal("32.15"),
        gd200=Decimal("30.60"),
        derivative_type="OPTIONSSCHEIN_CALL",
        derivative_wkn="JE85E1",
        derivative_indicated_price=Decimal("0.046"),
        derivative_currency="EUR",
        derivative_target_1=Decimal("0.24"),
        derivative_target_2=Decimal("0.79"),
        derivative_stop_1=Decimal("0.015"),
        derivative_stop_2=Decimal("0.046"),
        strike=Decimal("38.00"),
        strike_currency="USD",
        omega_or_leverage=Decimal("11.2"),
        maturity_date=date(2026, 12, 18),
        price_indication_at=datetime(2026, 7, 10, 8, 15),
        stock_upside_pct=Decimal("20"),
        stock_risk_pct=Decimal("-8"),
        derivative_upside_pct=Decimal("424"),
        derivative_risk_pct=Decimal("-67"),
        raw_text="source",
        validation_issues=(),
    )


def _job(*, status: str = "OPEN") -> ExternalObservationImportJobModel:
    return ExternalObservationImportJobModel(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        status=status,
        created_at=NOW,
        created_by=ACTOR_ID,
        updated_at=NOW,
    )


def _file(
    job_id: UUID,
    *,
    status: str = "PARSED",
    batch_id: UUID | None = None,
) -> ExternalObservationImportFileModel:
    return ExternalObservationImportFileModel(
        id=uuid4(),
        job_id=job_id,
        workspace_id=WORKSPACE_ID,
        import_batch_id=batch_id,
        original_filename="122-2026.pdf",
        content_hash="a" * 64,
        content_type="application/pdf",
        file_size_bytes=123,
        status=status,
        duplicate_of_file_id=None,
        failure_code=None,
        failure_detail=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _row(batch_id: UUID, *, status: str = "VALID") -> ExternalObservationImportRowModel:
    return ExternalObservationImportRowModel(
        id=uuid4(),
        batch_id=batch_id,
        workspace_id=WORKSPACE_ID,
        source_row_number=1,
        raw_payload=_json_payload(_recommendation()),
        validation_status=status,
        disposition="PENDING",
        resolved_underlying_id=uuid4(),
        resolved_product_id=uuid4(),
        target_external_observation_id=None,
        accepted_external_observation_version_id=None,
        disposed_at=None,
        disposed_by=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _session() -> Mock:
    session = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = Mock()
    session.add_all = Mock()
    return session


async def test_create_get_and_list_job_files() -> None:
    session = _session()
    service = ExternalObservationBulkImportService(session)

    created = await service.create_job(WORKSPACE_ID, ACTOR_ID)
    assert created.workspace_id == WORKSPACE_ID
    assert created.status == "OPEN"
    session.add.assert_called_once_with(created)
    session.commit.assert_awaited_once()

    session.scalar.return_value = created
    assert await service.get_job(WORKSPACE_ID, created.id) is created

    file_model = _file(created.id)
    session.scalars.return_value = [file_model]
    assert await service.list_files(WORKSPACE_ID, created.id) == [file_model]


async def test_get_job_rejects_unknown_workspace_job() -> None:
    session = _session()
    session.scalar.return_value = None
    service = ExternalObservationBulkImportService(session)

    with pytest.raises(BulkImportError, match="does not exist"):
        await service.get_job(WORKSPACE_ID, uuid4())


async def test_ingest_pdf_stages_valid_wkn_match(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    job = _job()
    underlying = UnderlyingModel(id=uuid4(), workspace_id=WORKSPACE_ID, wkn="A1H6GK")
    warrant = WarrantModel(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        issuer_id=uuid4(),
        underlying_id=underlying.id,
        display_name="Kinder Morgan Call",
        wkn="JE85E1",
    )
    session.scalar.side_effect = [job, None, None, underlying, warrant]
    session.scalars.return_value = ["PARSED"]
    monkeypatch.setattr(service_module, "parse_hebeltrader_pdf", lambda content: _recommendation())
    service = ExternalObservationBulkImportService(session)

    result = await service.ingest_pdf(
        job_id=job.id,
        workspace_id=WORKSPACE_ID,
        actor_id=ACTOR_ID,
        filename="122-2026.pdf",
        content_type="application/pdf",
        content=b"%PDF source",
    )

    assert result.status == "PARSED"
    assert result.import_batch_id is not None
    assert job.status == "READY"
    assert session.add.call_count >= 3
    session.commit.assert_awaited_once()


async def test_ingest_pdf_records_parse_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    job = _job()
    session.scalar.side_effect = [job, None, None]
    session.scalars.return_value = ["FAILED"]

    def fail(_: bytes) -> HebeltraderRecommendation:
        raise HebeltraderParseError("missing technical section")

    monkeypatch.setattr(service_module, "parse_hebeltrader_pdf", fail)
    service = ExternalObservationBulkImportService(session)

    result = await service.ingest_pdf(
        job_id=job.id,
        workspace_id=WORKSPACE_ID,
        actor_id=ACTOR_ID,
        filename="broken.pdf",
        content_type="application/pdf",
        content=b"%PDF broken",
    )

    assert result.status == "FAILED"
    assert result.failure_code == "HEBELTRADER_PARSE_FAILED"
    assert "technical section" in (result.failure_detail or "")
    assert job.status == "REVIEW_REQUIRED"


async def test_ingest_pdf_records_duplicate_without_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _session()
    job = _job()
    duplicate = _file(uuid4(), status="COMPLETED")
    session.scalar.side_effect = [job, None, duplicate]
    session.scalars.return_value = ["DUPLICATE"]
    parser = Mock()
    monkeypatch.setattr(service_module, "parse_hebeltrader_pdf", parser)
    service = ExternalObservationBulkImportService(session)

    result = await service.ingest_pdf(
        job_id=job.id,
        workspace_id=WORKSPACE_ID,
        actor_id=ACTOR_ID,
        filename="duplicate.pdf",
        content_type="application/pdf",
        content=b"same bytes",
    )

    assert result.status == "DUPLICATE"
    assert result.duplicate_of_file_id == duplicate.id
    parser.assert_not_called()
    assert job.status == "READY"


async def test_ingest_guards_filename_content_and_completed_job() -> None:
    session = _session()
    service = ExternalObservationBulkImportService(session)

    with pytest.raises(BulkImportError, match="filename"):
        await service.ingest_pdf(
            job_id=uuid4(),
            workspace_id=WORKSPACE_ID,
            actor_id=ACTOR_ID,
            filename=" ",
            content_type=None,
            content=b"x",
        )
    with pytest.raises(BulkImportError, match="empty"):
        await service.ingest_pdf(
            job_id=uuid4(),
            workspace_id=WORKSPACE_ID,
            actor_id=ACTOR_ID,
            filename="x.pdf",
            content_type=None,
            content=b"",
        )

    session.scalar.return_value = _job(status="COMPLETED")
    with pytest.raises(BulkImportError, match="cannot accept"):
        await service.ingest_pdf(
            job_id=uuid4(),
            workspace_id=WORKSPACE_ID,
            actor_id=ACTOR_ID,
            filename="x.pdf",
            content_type=None,
            content=b"x",
        )


async def test_resolve_review_row_validates_and_marks_file_parsed() -> None:
    session = _session()
    job = _job(status="REVIEW_REQUIRED")
    batch_id = uuid4()
    row = _row(batch_id, status="UNRESOLVED")
    row.resolved_underlying_id = None
    row.resolved_product_id = None
    file_model = _file(job.id, status="REVIEW_REQUIRED", batch_id=batch_id)
    pair_result = Mock()
    pair_result.one_or_none.return_value = (row, file_model)
    session.execute.return_value = pair_result
    underlying = UnderlyingModel(id=uuid4(), workspace_id=WORKSPACE_ID)
    warrant = WarrantModel(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        issuer_id=uuid4(),
        underlying_id=underlying.id,
        display_name="Call",
    )
    session.scalar.side_effect = [job, underlying, warrant]
    session.scalars.return_value = ["PARSED"]
    service = ExternalObservationBulkImportService(session)

    result = await service.resolve_review_row(
        workspace_id=WORKSPACE_ID,
        job_id=job.id,
        row_id=row.id,
        underlying_id=underlying.id,
        product_id=warrant.id,
        actor_id=ACTOR_ID,
    )

    assert result.validation_status == "VALID"
    assert result.resolved_underlying_id == underlying.id
    assert result.resolved_product_id == warrant.id
    assert file_model.status == "PARSED"
    assert "review_resolution" in result.raw_payload
    assert job.status == "READY"


async def test_resolve_rejects_warrant_for_different_underlying() -> None:
    session = _session()
    job = _job(status="REVIEW_REQUIRED")
    batch_id = uuid4()
    row = _row(batch_id, status="UNRESOLVED")
    file_model = _file(job.id, status="REVIEW_REQUIRED", batch_id=batch_id)
    pair_result = Mock()
    pair_result.one_or_none.return_value = (row, file_model)
    session.execute.return_value = pair_result
    underlying = UnderlyingModel(id=uuid4(), workspace_id=WORKSPACE_ID)
    warrant = WarrantModel(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        issuer_id=uuid4(),
        underlying_id=uuid4(),
        display_name="Wrong Call",
    )
    session.scalar.side_effect = [job, underlying, warrant]
    service = ExternalObservationBulkImportService(session)

    with pytest.raises(BulkImportError, match="does not belong"):
        await service.resolve_review_row(
            workspace_id=WORKSPACE_ID,
            job_id=job.id,
            row_id=row.id,
            underlying_id=underlying.id,
            product_id=warrant.id,
            actor_id=ACTOR_ID,
        )


async def test_discard_review_row_completes_file() -> None:
    session = _session()
    job = _job(status="REVIEW_REQUIRED")
    batch_id = uuid4()
    row = _row(batch_id, status="UNRESOLVED")
    file_model = _file(job.id, status="REVIEW_REQUIRED", batch_id=batch_id)
    pair_result = Mock()
    pair_result.one_or_none.return_value = (row, file_model)
    session.execute.return_value = pair_result
    session.scalar.return_value = job
    session.scalars.return_value = ["COMPLETED"]
    service = ExternalObservationBulkImportService(session)

    result = await service.discard_review_row(
        workspace_id=WORKSPACE_ID,
        job_id=job.id,
        row_id=row.id,
        actor_id=ACTOR_ID,
    )

    assert result.disposition == "DISCARDED"
    assert result.disposed_by == ACTOR_ID
    assert file_model.status == "COMPLETED"
    assert job.status == "READY"


async def test_confirm_job_materializes_observation_and_evidence_only() -> None:
    session = _session()
    job = _job(status="READY")
    batch_id = uuid4()
    file_model = _file(job.id, status="PARSED", batch_id=batch_id)
    row = _row(batch_id)
    session.scalar.side_effect = [job, job, job, file_model]
    session.scalars.side_effect = [[file_model], [], [row]]
    service = ExternalObservationBulkImportService(session)

    version_ids = await service.confirm_job(
        workspace_id=WORKSPACE_ID,
        job_id=job.id,
        actor_id=ACTOR_ID,
    )

    assert len(version_ids) == 1
    assert row.disposition == "ACCEPTED"
    assert row.accepted_external_observation_version_id == version_ids[0]
    assert file_model.status == "COMPLETED"
    assert job.status == "COMPLETED"
    persisted = session.add_all.call_args.args[0]
    assert {type(item).__name__ for item in persisted} == {
        "ExternalObservationModel",
        "ExternalObservationVersionModel",
        "LearningEvidenceModel",
        "ExternalObservationEvidenceModel",
    }
    assert all("Trade" not in type(item).__name__ for item in persisted)
    session.commit.assert_awaited_once()


async def test_confirm_job_blocks_failed_files_and_review_rows() -> None:
    session = _session()
    job = _job(status="REVIEW_REQUIRED")
    failed = _file(job.id, status="FAILED")
    session.scalar.side_effect = [job, job]
    session.scalars.return_value = [failed]
    service = ExternalObservationBulkImportService(session)

    with pytest.raises(BulkImportError, match="failed files"):
        await service.confirm_job(
            workspace_id=WORKSPACE_ID,
            job_id=job.id,
            actor_id=ACTOR_ID,
        )

    session = _session()
    job = _job(status="REVIEW_REQUIRED")
    parsed = _file(job.id, status="PARSED")
    review = _row(uuid4(), status="UNRESOLVED")
    session.scalar.side_effect = [job, job, job]
    session.scalars.side_effect = [[parsed], [review]]
    service = ExternalObservationBulkImportService(session)
    with pytest.raises(BulkImportError, match="review rows"):
        await service.confirm_job(
            workspace_id=WORKSPACE_ID,
            job_id=job.id,
            actor_id=ACTOR_ID,
        )


def test_payload_helpers_preserve_source_values_and_validate_date() -> None:
    payload = _json_payload(_recommendation())
    assert payload["issue_date"] == "2026-07-10"
    assert payload["derivative_indicated_price"] == "0.046"
    assert "raw_text" not in payload
    assert _observed_at(payload) == datetime(2026, 7, 10, tzinfo=UTC)

    with pytest.raises(BulkImportError, match="no valid issue_date"):
        _observed_at({})
    with pytest.raises(BulkImportError, match="invalid issue_date"):
        _observed_at({"issue_date": "not-a-date"})

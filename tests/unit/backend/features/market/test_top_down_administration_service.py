from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.market.domain.top_down import BenchmarkRole, MarketReferenceType
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)


def _session():
    session = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = Mock()
    return session


@pytest.mark.asyncio
async def test_bootstrap_and_list_paths_cover_existing_and_new_references():
    session = _session()
    existing = SimpleNamespace(code="DAX")
    session.scalar = AsyncMock(side_effect=[existing, None, None])
    service = TopDownReferenceAdministrationService(session)

    result = await service.bootstrap_v1(uuid4())

    assert len(result.market_references) == 3
    assert result.market_references[0] is existing
    assert session.add.call_count == 2
    session.commit.assert_awaited_once()

    scalar_result = Mock()
    scalar_result.all.return_value = [existing]
    session.scalars = AsyncMock(return_value=scalar_result)
    assert await service.list_market_references(uuid4()) == (existing,)
    assert await service.list_sectors(uuid4()) == (existing,)


@pytest.mark.asyncio
async def test_create_and_activate_sector_and_reference():
    session = _session()
    service = TopDownReferenceAdministrationService(session)
    workspace = uuid4()

    session.scalar.return_value = None
    sector = await service.create_sector(
        workspace_id=workspace,
        code=" tech ",
        name=" Technology ",
        classification_system=" TEST ",
        classification_version=" 1 ",
    )
    assert sector.code == "TECH"
    assert sector.name == "Technology"

    session.scalar.return_value = object()
    with pytest.raises(ValueError, match="sector code already exists"):
        await service.create_sector(
            workspace_id=workspace,
            code="tech",
            name="T",
            classification_system="X",
            classification_version="1",
        )

    reference = SimpleNamespace(active=False)
    session.scalar.return_value = reference
    assert (
        await service.set_market_reference_active(
            workspace_id=workspace, market_reference_id=uuid4(), active=True
        )
    ).active
    sector_obj = SimpleNamespace(active=True)
    session.scalar.return_value = sector_obj
    assert not (
        await service.set_sector_active(workspace_id=workspace, sector_id=uuid4(), active=False)
    ).active

    session.scalar.return_value = None
    with pytest.raises(ValueError, match="market reference not found"):
        await service.set_market_reference_active(
            workspace_id=workspace, market_reference_id=uuid4(), active=True
        )
    with pytest.raises(ValueError, match="sector not found"):
        await service.set_sector_active(workspace_id=workspace, sector_id=uuid4(), active=True)


@pytest.mark.asyncio
async def test_create_sector_reference_and_duplicate_rejected():
    session = _session()
    service = TopDownReferenceAdministrationService(session)
    workspace = uuid4()
    session.scalar.return_value = None
    value = await service.create_sector_reference(
        workspace_id=workspace,
        code=" tech_idx ",
        name=" Tech Index ",
        region=" us ",
        reference_version=" v1 ",
    )
    assert value.code == "TECH_IDX"
    assert value.reference_type == MarketReferenceType.SECTOR_INDEX.value
    assert value.role == BenchmarkRole.SECTOR_REFERENCE.value
    assert value.region == "US"

    session.scalar.return_value = object()
    with pytest.raises(ValueError, match="market reference code already exists"):
        await service.create_sector_reference(
            workspace_id=workspace,
            code="TECH_IDX",
            name="x",
            region="US",
            reference_version="1",
        )


@pytest.mark.asyncio
async def test_assignment_creation_paths_and_validation():
    session = _session()
    service = TopDownReferenceAdministrationService(session)
    workspace, underlying, sector_id, ref_id, listing_id = (uuid4() for _ in range(5))
    service._require_reference = AsyncMock(
        return_value=SimpleNamespace(reference_type=MarketReferenceType.SECTOR_INDEX.value)
    )
    service._require_underlying = AsyncMock(return_value=object())
    service._require_sector = AsyncMock(return_value=object())
    service._ensure_no_overlap = AsyncMock(return_value=None)

    session.scalar.return_value = SimpleNamespace(id=listing_id)
    listing_assignment = await service.assign_reference_listing(
        workspace_id=workspace,
        market_reference_id=ref_id,
        listing_id=listing_id,
        valid_from=date(2026, 1, 1),
        valid_to=None,
        source=" admin ",
        source_reference="  ref  ",
        quality_status="GOOD",
    )
    assert listing_assignment.source == "admin"
    assert listing_assignment.source_reference == "ref"

    benchmark = await service.assign_underlying_benchmark(
        workspace_id=workspace,
        underlying_id=underlying,
        market_reference_id=ref_id,
        role=BenchmarkRole.BROAD_MARKET,
        valid_from=date(2026, 1, 1),
        valid_to=None,
        source=" admin ",
        source_reference=" ",
        quality_status="GOOD",
    )
    assert benchmark.role == BenchmarkRole.BROAD_MARKET.value
    assert benchmark.source_reference is None

    sector_assignment = await service.assign_underlying_sector(
        workspace_id=workspace,
        underlying_id=underlying,
        sector_id=sector_id,
        valid_from=date(2026, 1, 1),
        valid_to=None,
        source=" admin ",
        source_reference=None,
        quality_status="GOOD",
    )
    assert sector_assignment.sector_id == sector_id

    sector_ref = await service.assign_sector_reference(
        workspace_id=workspace,
        sector_id=sector_id,
        market_reference_id=ref_id,
        valid_from=date(2026, 1, 1),
        valid_to=None,
        source=" admin ",
        quality_status="GOOD",
    )
    assert sector_ref.market_reference_id == ref_id

    service._require_reference.return_value = SimpleNamespace(
        reference_type=MarketReferenceType.INDEX.value
    )
    with pytest.raises(ValueError, match="SECTOR_INDEX"):
        await service.assign_sector_reference(
            workspace_id=workspace,
            sector_id=sector_id,
            market_reference_id=ref_id,
            valid_from=date(2026, 1, 1),
            valid_to=None,
            source="admin",
            quality_status="GOOD",
        )


@pytest.mark.asyncio
async def test_assignment_missing_listing_and_helper_validation():
    session = _session()
    service = TopDownReferenceAdministrationService(session)
    workspace = uuid4()
    service._require_reference = AsyncMock(return_value=object())
    session.scalar.return_value = None
    with pytest.raises(ValueError, match="listing not found"):
        await service.assign_reference_listing(
            workspace_id=workspace,
            market_reference_id=uuid4(),
            listing_id=uuid4(),
            valid_from=date(2026, 1, 1),
            valid_to=None,
            source="x",
            source_reference=None,
            quality_status="GOOD",
        )

    raw = TopDownReferenceAdministrationService(_session())
    with pytest.raises(ValueError, match="valid_to"):
        await raw._ensure_no_overlap(
            object, workspace, date(2026, 2, 1), date(2026, 1, 1), label="x"
        )

    class FakeModel:
        id = SimpleNamespace()
        workspace_id = SimpleNamespace()
        valid_from = SimpleNamespace()
        valid_to = SimpleNamespace()

    # cover the overlap branch without relying on actual SQL execution
    overlap_session = _session()
    overlap_session.scalar.return_value = uuid4()
    overlap_service = TopDownReferenceAdministrationService(overlap_session)
    # SQL construction requires mapped attributes; use a real assignment model
    # indirectly through a patched scalar path.
    from app.features.market.persistence.top_down_models import (
        UnderlyingSectorAssignmentModel,
    )

    with pytest.raises(ValueError, match="overlapping x"):
        await overlap_service._ensure_no_overlap(
            UnderlyingSectorAssignmentModel,
            workspace,
            date(2026, 1, 1),
            None,
            UnderlyingSectorAssignmentModel.underlying_id == uuid4(),
            label="x",
        )

    assert raw._clean(None) is None
    assert raw._clean("   ") is None
    assert raw._clean(" x ") == "x"

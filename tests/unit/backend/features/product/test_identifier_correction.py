from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.market.domain.enums import AggregateType
from app.features.market_data.domain.enums import MappingStatus
from app.features.product.service.application import WarrantService
from app.features.product.service.errors import (
    DuplicateWarrantIsin,
    WarrantConcurrentModification,
    WarrantServiceError,
)


def setup():
    session = AsyncMock()
    session.add = Mock()
    session.scalar.return_value = None
    model = SimpleNamespace(id=uuid4(), isin="DE000PK72H6", wkn=None, version=1)
    service = WarrantService(session)
    service.get = AsyncMock(return_value=model)
    mapping = SimpleNamespace(status=MappingStatus.ACTIVE, validated_at="old", version=2)
    session.scalars.return_value = [mapping]
    return session, model, service, mapping


@pytest.mark.asyncio
async def test_correction_keeps_product_identity_audits_and_invalidates_mapping():
    session, model, service, mapping = setup()
    original_id = model.id
    result = await service.correct_identifiers(
        uuid4(),
        model.id,
        expected_version=1,
        isin="DE000VH2LU21",
        wkn="VH2LU2",
        evidence="Test document; same instrument identity confirmed",
    )
    assert result is model and result.id == original_id
    assert (model.isin, model.wkn, model.version) == ("DE000VH2LU21", "VH2LU2", 2)
    assert mapping.status == MappingStatus.INVALID and mapping.validated_at is None
    assert mapping.version == 3
    audit = session.add.call_args.args[0]
    assert audit.aggregate_id == original_id and audit.aggregate_type == AggregateType.WARRANT
    assert audit.field_changes["isin"] == {"old": "DE000PK72H6", "new": "DE000VH2LU21"}
    assert audit.version_before == 1 and audit.version_after == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "isin,wkn,evidence",
    [
        ("DE000PK72H6", None, "Document"),
        ("DE000VH2LU20", None, "Document"),
        ("DE000VH2LU21", "VH2LU", "Document"),
        ("DE000VH2LU21", None, " "),
    ],
)
async def test_invalid_identifiers_or_missing_evidence_do_not_mutate(isin, wkn, evidence):
    session, model, service, _ = setup()
    with pytest.raises((ValueError, WarrantServiceError)):
        await service.correct_identifiers(
            uuid4(), model.id, expected_version=1, isin=isin, wkn=wkn, evidence=evidence
        )
    assert model.isin == "DE000PK72H6" and model.version == 1
    session.commit.assert_not_awaited()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_stale_version_and_duplicate_do_not_modify_product():
    session, model, service, _ = setup()
    args = dict(isin="DE000VH2LU21", wkn=None, evidence="Document")
    with pytest.raises(WarrantConcurrentModification):
        await service.correct_identifiers(uuid4(), model.id, expected_version=2, **args)
    session.scalar.return_value = uuid4()
    with pytest.raises(DuplicateWarrantIsin):
        await service.correct_identifiers(uuid4(), model.id, expected_version=1, **args)
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unchanged_identifiers_do_not_invalidate_or_increment():
    session, model, service, _ = setup()
    model.isin = "DE000VH2LU21"
    assert (
        await service.correct_identifiers(
            uuid4(), model.id, expected_version=1, isin=model.isin, wkn=None, evidence="Document"
        )
        is model
    )
    session.scalars.assert_not_awaited()
    session.commit.assert_not_awaited()

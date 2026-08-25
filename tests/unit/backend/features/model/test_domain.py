from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.features.model.domain.enums import (
    HypothesisStatus,
    ModelVersionStatus,
    ValidationConclusion,
    ValidationMethod,
)
from app.features.model.domain.models import (
    GovernedModel,
    Hypothesis,
    ModelValidation,
    ModelVersion,
)


NOW = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


def test_governed_model_requires_identity_fields() -> None:
    with pytest.raises(ValueError, match="model_key"):
        GovernedModel(uuid4(), uuid4(), " ", "Name", "Purpose", NOW, uuid4())


def test_initial_model_version_is_immutable_snapshot() -> None:
    version = ModelVersion(
        id=uuid4(),
        model_id=uuid4(),
        version=1,
        status=ModelVersionStatus.DRAFT,
        definition={"threshold": 5},
        change_summary="Initial",
        created_at=NOW,
        created_by=uuid4(),
    )
    assert version.definition == {"threshold": 5}
    with pytest.raises(ValueError, match="predecessor"):
        ModelVersion(
            id=uuid4(),
            model_id=uuid4(),
            version=1,
            status=ModelVersionStatus.DRAFT,
            definition={"threshold": 5},
            change_summary="Initial",
            created_at=NOW,
            created_by=uuid4(),
            previous_version_id=uuid4(),
        )


def test_later_model_version_requires_predecessor() -> None:
    with pytest.raises(ValueError, match="requires predecessor"):
        ModelVersion(
            id=uuid4(),
            model_id=uuid4(),
            version=2,
            status=ModelVersionStatus.APPROVED,
            definition={"threshold": 7},
            change_summary="Tune threshold",
            created_at=NOW,
            created_by=uuid4(),
        )


def test_hypothesis_requires_nonblank_statement() -> None:
    with pytest.raises(ValueError, match="statement"):
        Hypothesis(
            id=uuid4(),
            workspace_id=uuid4(),
            title="Gap-up filter",
            statement=" ",
            status=HypothesisStatus.OPEN,
            created_at=NOW,
            created_by=uuid4(),
        )


def test_validation_rejects_future_cutoff() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        ModelValidation(
            id=uuid4(),
            proposal_id=uuid4(),
            method=ValidationMethod.RETROSPECTIVE,
            evidence_cutoff_at=NOW + timedelta(seconds=1),
            conclusion=ValidationConclusion.INCONCLUSIVE,
            metrics={},
            notes=None,
            created_at=NOW,
            created_by=uuid4(),
        )

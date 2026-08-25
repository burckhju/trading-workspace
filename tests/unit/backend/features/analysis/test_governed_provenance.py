from uuid import uuid4

from app.features.analysis.domain.governed_provenance import (
    IMPLEMENTATION_REF,
    RUNTIME_CONTRACT,
    governed_baseline_definition,
    matches_governed_baseline,
)
from app.features.analysis.persistence.models import (
    MarketAnalysisRunModel,
    attach_governed_model_provenance,
)


class _Dialect:
    def __init__(self, name: str) -> None:
        self.name = name


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


class _CandidatesResult:
    def __init__(self, values: tuple[object, ...]) -> None:
        self._values = values

    def scalars(self) -> tuple[object, ...]:
        return self._values


class _Connection:
    def __init__(
        self,
        *,
        dialect: str = "postgresql",
        workspace_id: object | None = None,
        candidates: tuple[object, ...] = (),
    ) -> None:
        self.dialect = _Dialect(dialect)
        self._results = [
            _ScalarResult(workspace_id),
            _CandidatesResult(candidates),
        ]
        self.execute_count = 0

    def execute(self, _statement: object) -> object:
        result = self._results[self.execute_count]
        self.execute_count += 1
        return result


def _run() -> MarketAnalysisRunModel:
    return MarketAnalysisRunModel(
        analysis_id=uuid4(),
        model_id="EOD_TREND_MOMENTUM",
        model_version="1.0.0",
    )


def test_governed_baseline_definition_identifies_released_runtime() -> None:
    definition = governed_baseline_definition()

    assert definition == {
        "runtime_contract": RUNTIME_CONTRACT,
        "runtime_model_id": "EOD_TREND_MOMENTUM",
        "runtime_model_version": "1.0.0",
        "implementation_ref": IMPLEMENTATION_REF,
        "rule_representation": "CODE_PLUS_PARAMETERS",
    }
    assert matches_governed_baseline(definition) is True


def test_governed_baseline_rejects_different_runtime_definition() -> None:
    definition = governed_baseline_definition()
    definition["runtime_model_version"] = "2.0.0"

    assert matches_governed_baseline(definition) is False


def test_market_analysis_run_has_nullable_governed_version_fk() -> None:
    column = MarketAnalysisRunModel.__table__.c.governed_model_version_id

    assert column.nullable is True
    assert {fk.target_fullname for fk in column.foreign_keys} == {"governed_model_versions.id"}


def test_resolver_attaches_exactly_one_matching_approved_baseline() -> None:
    governed_version_id = uuid4()
    connection = _Connection(workspace_id=uuid4(), candidates=(governed_version_id,))
    run = _run()

    attach_governed_model_provenance(None, connection, run)  # type: ignore[arg-type]

    assert run.governed_model_version_id == governed_version_id
    assert connection.execute_count == 2


def test_resolver_keeps_provenance_empty_when_baseline_is_ambiguous() -> None:
    connection = _Connection(workspace_id=uuid4(), candidates=(uuid4(), uuid4()))
    run = _run()

    attach_governed_model_provenance(None, connection, run)  # type: ignore[arg-type]

    assert run.governed_model_version_id is None


def test_resolver_keeps_provenance_empty_without_workspace() -> None:
    connection = _Connection(workspace_id=None)
    run = _run()

    attach_governed_model_provenance(None, connection, run)  # type: ignore[arg-type]

    assert run.governed_model_version_id is None
    assert connection.execute_count == 1


def test_resolver_does_not_run_governance_lookup_on_non_postgres() -> None:
    connection = _Connection(dialect="sqlite")
    run = _run()

    attach_governed_model_provenance(None, connection, run)  # type: ignore[arg-type]

    assert run.governed_model_version_id is None
    assert connection.execute_count == 0

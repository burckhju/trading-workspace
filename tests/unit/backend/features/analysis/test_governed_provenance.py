from app.features.analysis.domain.governed_provenance import (
    IMPLEMENTATION_REF,
    RUNTIME_CONTRACT,
    governed_baseline_definition,
    matches_governed_baseline,
)
from app.features.analysis.persistence.models import MarketAnalysisRunModel


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

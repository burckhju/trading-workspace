"""Transport and governed provenance preserve exact immutable calculation contracts."""

import pytest
from pydantic import ValidationError

from app.features.analysis.api.dtos import RunAnalysisRequest
from app.features.analysis.domain.governed_provenance import (
    governed_baseline_definition,
    governed_runtime_definition,
)


def test_new_run_without_override_uses_fixed_corrected_contract():
    request = RunAnalysisRequest(start_date="2026-01-01", end_date="2026-10-23")
    assert request.model_version == "1.0.1"


@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
def test_request_accepts_only_an_exact_available_version(version):
    request = RunAnalysisRequest(
        start_date="2026-01-01", end_date="2026-10-23", model_version=version
    )
    assert request.model_version == version


@pytest.mark.parametrize("version", ["latest", "1.0", "1.0.2", " 1.0.1", "", None])
def test_unknown_version_is_not_silently_ignored(version):
    with pytest.raises(ValidationError):
        RunAnalysisRequest(start_date="2026-01-01", end_date="2026-10-23", model_version=version)


def test_legacy_governed_definition_is_unchanged_and_new_contract_is_distinct():
    legacy = governed_baseline_definition()
    expected_legacy = governed_runtime_definition(
        model_id="EOD_TREND_MOMENTUM", model_version="1.0.0"
    )
    assert expected_legacy == legacy
    corrected = governed_runtime_definition(model_id="EOD_TREND_MOMENTUM", model_version="1.0.1")
    assert corrected["runtime_model_version"] == "1.0.1"
    assert corrected["runtime_contract"] != legacy["runtime_contract"]
    assert corrected["implementation_ref"] != legacy["implementation_ref"]
    assert corrected["implementation_ref"].endswith("@541fcadfd77bde314e774b19a50af2ed61900d0c")
    assert legacy["runtime_model_version"] == "1.0.0"


@pytest.mark.parametrize("model,version", [("OTHER", "1.0.1"), ("EOD_TREND_MOMENTUM", "latest")])
def test_unknown_runtime_has_no_governed_provenance_contract(model, version):
    assert governed_runtime_definition(model_id=model, model_version=version) is None

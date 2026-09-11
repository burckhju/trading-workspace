from app.features.position_monitoring.service.phase_engine import PHASE_POLICY_VERSION


def test_phase_policy_version_is_explicit() -> None:
    assert PHASE_POLICY_VERSION == "POSITION_PHASE_V1"

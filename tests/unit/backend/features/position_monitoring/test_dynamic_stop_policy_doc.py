from pathlib import Path


def test_dynamic_stop_policy_document_locks_v1_contract() -> None:
    path = Path("app/features/position_monitoring/service/dynamic_stop.md")
    content = path.read_text(encoding="utf-8")
    assert "DYNAMIC_STOP_V1" in content
    assert "read-only" in content

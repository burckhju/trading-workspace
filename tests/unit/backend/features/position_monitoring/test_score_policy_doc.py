from pathlib import Path


def test_score_policy_document_names_version() -> None:
    content = Path("app/features/position_monitoring/service/score_engine.md").read_text()
    assert "POSITION_SCORE_V1" in content

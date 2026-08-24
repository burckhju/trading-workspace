from pathlib import Path

MIGRATION = (
    Path(__file__).parents[5]
    / "backend"
    / "migrations"
    / "versions"
    / "20260820_0020_ft012_learning_slice_01.py"
)


def test_external_observation_ddl_is_in_0020() -> None:
    text = MIGRATION.read_text()
    for table in (
        "external_observation_import_batches",
        "external_observation_import_rows",
        "external_observation_import_row_issues",
        "external_observations",
        "external_observation_versions",
        "external_observation_journals",
        "external_observation_journal_versions",
    ):
        assert f'"{table}"' in text


def test_external_observation_current_pointer_is_deferred() -> None:
    text = MIGRATION.read_text()
    assert "fk_external_observations_current_version_same_observation" in text
    assert "deferrable=True" in text
    assert 'initially="DEFERRED"' in text


def test_external_journal_has_one_open_draft_partial_index() -> None:
    text = MIGRATION.read_text()
    assert "uq_external_observation_journal_versions_open_draft" in text
    assert "status = 'DRAFT'" in text

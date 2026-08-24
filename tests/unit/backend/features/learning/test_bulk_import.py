from datetime import UTC, datetime
from uuid import uuid4

from app.features.learning.domain.bulk_import import (
    ExternalObservationImportFile,
    ExternalObservationImportFileStatus,
    ExternalObservationImportJobSummary,
)


def test_bulk_import_contract_supports_more_than_one_hundred_files() -> None:
    now = datetime.now(UTC)
    job_id = uuid4()
    workspace_id = uuid4()

    files = tuple(
        ExternalObservationImportFile(
            id=uuid4(),
            job_id=job_id,
            workspace_id=workspace_id,
            import_batch_id=None,
            original_filename=f"Hebeltrader_2026-{number:03d}.pdf",
            content_hash=f"{number:064x}",
            content_type="application/pdf",
            file_size_bytes=1000 + number,
            status=ExternalObservationImportFileStatus.QUEUED,
            duplicate_of_file_id=None,
            failure_code=None,
            failure_detail=None,
            created_at=now,
            updated_at=now,
        )
        for number in range(1, 126)
    )

    assert len(files) == 125
    assert all(value.status is ExternalObservationImportFileStatus.QUEUED for value in files)


def test_job_summary_has_separate_failure_and_duplicate_counts() -> None:
    summary = ExternalObservationImportJobSummary(
        files_total=126,
        files_queued=0,
        files_parsed=0,
        files_review_required=5,
        files_duplicate=2,
        files_failed=1,
        files_completed=118,
    )

    assert summary.files_total == 126
    assert summary.files_completed == 118
    assert summary.files_review_required == 5
    assert summary.files_duplicate == 2
    assert summary.files_failed == 1

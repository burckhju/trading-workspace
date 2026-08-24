from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.learning.domain import (
    ExternalObservationImportBatch,
    ExternalObservationRecordingMethod,
    ExternalObservationVersion,
)

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def test_file_import_requires_import_provenance() -> None:
    with pytest.raises(ValueError):
        ExternalObservationVersion(
            id=uuid4(),
            external_observation_id=uuid4(),
            version=1,
            underlying_id=uuid4(),
            product_id=None,
            source_type="RESEARCH",
            source_name="Source",
            external_reference=None,
            observed_at=NOW,
            recorded_at=NOW,
            imported_at=None,
            recording_method=ExternalObservationRecordingMethod.FILE_IMPORT,
            import_row_id=None,
            source_metadata=None,
            supersedes_version_id=None,
            created_at=NOW,
            created_by=uuid4(),
        )


def test_import_batch_requires_sha256_length() -> None:
    with pytest.raises(ValueError):
        ExternalObservationImportBatch(
            id=uuid4(),
            workspace_id=uuid4(),
            original_filename="input.csv",
            content_hash="bad",
            content_type="text/csv",
            file_size_bytes=1,
            imported_at=NOW,
            imported_by=uuid4(),
        )

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.bulk_import_dependencies import get_bulk_import_service
from app.features.learning.application.bulk_import_service import BulkImportError


class FakeBulkImportService:
    def __init__(self) -> None:
        self.job_id = uuid4()
        self.batch_id = uuid4()
        self.row_id = uuid4()
        self.file_id = uuid4()
        self.version_id = uuid4()
        self.error: BulkImportError | None = None
        self.ingested: list[str] = []
        self.review_rows = [self._row()]
        self.files: list[SimpleNamespace] = []

    def _raise(self) -> None:
        if self.error is not None:
            raise self.error

    def _job(self, status: str = "REVIEW_REQUIRED") -> SimpleNamespace:
        return SimpleNamespace(id=self.job_id, status=status)

    def _file(
        self,
        status: str = "REVIEW_REQUIRED",
        *,
        filename: str = "issue.pdf",
    ) -> SimpleNamespace:
        return SimpleNamespace(
            id=uuid4(),
            original_filename=filename,
            status=status,
            duplicate_of_file_id=None,
            failure_code=None,
            failure_detail=None,
        )

    def _row(self, status: str = "UNRESOLVED", disposition: str = "PENDING") -> SimpleNamespace:
        return SimpleNamespace(
            id=self.row_id,
            batch_id=self.batch_id,
            validation_status=status,
            disposition=disposition,
            resolved_underlying_id=None,
            resolved_product_id=None,
            raw_payload={"underlying_wkn": "A1H6GK", "derivative_wkn": "JE85E1"},
        )

    async def create_job(self, workspace_id, actor_id):
        del workspace_id, actor_id
        self._raise()
        return self._job("OPEN")

    async def ingest_pdf(self, **kwargs):
        self._raise()
        filename = kwargs["filename"]
        self.ingested.append(filename)
        model = self._file(filename=filename)
        self.files.append(model)
        return model

    async def get_job(self, workspace_id, job_id):
        del workspace_id, job_id
        self._raise()
        return self._job()

    async def list_files(self, workspace_id, job_id):
        del workspace_id, job_id
        self._raise()
        return self.files

    async def list_review_rows(self, workspace_id, job_id):
        del workspace_id, job_id
        self._raise()
        return self.review_rows

    async def resolve_review_row(self, **kwargs):
        self._raise()
        row = self._row("VALID")
        row.resolved_underlying_id = kwargs["underlying_id"]
        row.resolved_product_id = kwargs["product_id"]
        self.review_rows = []
        return row

    async def discard_review_row(self, **kwargs):
        del kwargs
        self._raise()
        row = self._row("UNRESOLVED", "DISCARDED")
        self.review_rows = []
        return row

    async def confirm_job(self, **kwargs):
        del kwargs
        self._raise()
        return [self.version_id]


def _client(service: FakeBulkImportService) -> TestClient:
    app = _make_app()
    app.dependency_overrides[get_bulk_import_service] = lambda: service
    return TestClient(app)


def test_bulk_upload_and_job_status_routes() -> None:
    service = FakeBulkImportService()
    client = _client(service)

    response = client.post(
        "/api/v1/learning/bulk-imports/hebeltrader",
        files=[
            ("files", ("a.pdf", b"%PDF a", "application/pdf")),
            ("files", ("b.pdf", b"%PDF b", "application/pdf")),
        ],
    )
    assert response.status_code == 201
    assert response.json()["job_id"] == str(service.job_id)
    assert response.json()["files_total"] == 2
    assert response.json()["files_by_status"] == {"REVIEW_REQUIRED": 2}
    assert service.ingested == ["a.pdf", "b.pdf"]

    status = client.get(f"/api/v1/learning/bulk-imports/{service.job_id}")
    assert status.status_code == 200
    assert status.json()["files"][0]["filename"] == "a.pdf"


def test_review_resolve_discard_and_confirm_routes() -> None:
    service = FakeBulkImportService()
    client = _client(service)

    review = client.get(f"/api/v1/learning/bulk-imports/{service.job_id}/review")
    assert review.status_code == 200
    assert review.json()[0]["payload"]["underlying_wkn"] == "A1H6GK"

    underlying_id = uuid4()
    product_id = uuid4()
    resolved = client.post(
        f"/api/v1/learning/bulk-imports/{service.job_id}/review/{service.row_id}/resolve",
        json={"underlying_id": str(underlying_id), "product_id": str(product_id)},
    )
    assert resolved.status_code == 200
    assert resolved.json()["validation_status"] == "VALID"
    assert resolved.json()["underlying_id"] == str(underlying_id)

    service.review_rows = [service._row()]
    discarded = client.post(
        f"/api/v1/learning/bulk-imports/{service.job_id}/review/{service.row_id}/discard"
    )
    assert discarded.status_code == 200
    assert discarded.json()["disposition"] == "DISCARDED"

    confirmed = client.post(f"/api/v1/learning/bulk-imports/{service.job_id}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["accepted_observation_version_ids"] == [str(service.version_id)]


def test_bulk_import_routes_map_service_errors() -> None:
    service = FakeBulkImportService()
    service.error = BulkImportError("bad import")
    client = _client(service)

    upload = client.post(
        "/api/v1/learning/bulk-imports/hebeltrader",
        files=[("files", ("a.pdf", b"%PDF", "application/pdf"))],
    )
    assert upload.status_code == 400
    assert upload.json()["code"] == "HTTP_400"
    assert upload.json()["message"] == "bad import"

    status = client.get(f"/api/v1/learning/bulk-imports/{service.job_id}")
    assert status.status_code == 404

    review = client.get(f"/api/v1/learning/bulk-imports/{service.job_id}/review")
    assert review.status_code == 404

    resolve = client.post(
        f"/api/v1/learning/bulk-imports/{service.job_id}/review/{service.row_id}/resolve",
        json={"underlying_id": str(uuid4()), "product_id": str(uuid4())},
    )
    assert resolve.status_code == 400

    discard = client.post(
        f"/api/v1/learning/bulk-imports/{service.job_id}/review/{service.row_id}/discard"
    )
    assert discard.status_code == 400

    confirm = client.post(f"/api/v1/learning/bulk-imports/{service.job_id}/confirm")
    assert confirm.status_code == 400

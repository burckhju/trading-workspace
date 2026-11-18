"""Only synthetic local files and intercepted HTTP; never a user's depot/API."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import stat
import sys
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request
from uuid import uuid4

import pytest

REPO = Path(__file__).resolve().parents[3]
WORKSPACE = "00000000-0000-4000-8000-000000000001"
ISIN = "DE000TEST124"
ISIN_SECOND = "DE000ZZ00002"


@pytest.fixture
def script() -> ModuleType:
    name = "import_original_product_documents_test"
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts/import-original-product-documents.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def disposable_source() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(
        prefix="tw_product_original_import_test_", dir=REPO.parent
    ) as directory:
        path = Path(directory).resolve()
        assert not path.is_relative_to(REPO)
        yield path


def original(isin: str = ISIN, wkn: str = "TEST12") -> bytes:
    return (
        '\ufeff<!doctype html>\r\n<html><head><link rel="canonical" '
        'href="https://www.boerse-stuttgart.de/de-de/produkte/hebelprodukte/'
        f'optionsscheine/stuttgart/{wkn.lower()}/">'
        f"<title>Synthetisch {wkn} | Börse Stuttgart (XSTU)</title></head><body>"
        f"<div><h1>Synthetischer Call</h1><span>WKN {wkn}</span><span>ISIN {isin}</span></div>"
        f'<section id="MasterDataBlock-synthetic">ISIN {isin} WKN {wkn}<table>'
        "<tr><td>Letzter Börsenhandelstag</td><td>18.12.2026</td></tr>"
        "</table></section></body></html>\r\n"
    ).encode()


def write_original(directory: Path, *, second: bool = False) -> Path:
    isin, wkn = (ISIN_SECOND, "ZZ0000") if second else (ISIN, "TEST12")
    path = directory / f"{isin}-xstu.html"
    path.write_bytes(original(isin, wkn))
    return path


class FakeResponse(io.BytesIO):
    def __init__(self, payload: Any, status: int) -> None:
        super().__init__(json.dumps(payload).encode())
        self.status = status


class SyntheticProductApi:
    def __init__(self) -> None:
        self.calls: list[Request] = []
        self.products = [
            {
                "id": str(uuid4()),
                "workspace_id": WORKSPACE,
                "isin": ISIN,
                "wkn": None,
                "display_name": "Synthetischer Call 1",
            },
            {
                "id": str(uuid4()),
                "workspace_id": WORKSPACE,
                "isin": ISIN_SECOND,
                "wkn": "ZZ0000",
                "display_name": "Synthetischer Call 2",
            },
        ]
        self.imported: dict[str, bytes] = {}
        self.revisions: dict[str, int] = {}
        self.api_status = "AVAILABLE"
        self.fail_current: int | None = None
        self.fail_import: int | None = None
        self.handlers: tuple[Any, ...] = ()

    def build_opener(self, *handlers: Any) -> SyntheticProductApi:
        self.handlers = handlers
        return self

    def open(self, request: Request, timeout: int) -> FakeResponse:
        assert timeout == 30
        assert request.full_url.startswith("http://127.0.0.1:8000/api/v1/warrants")
        assert request.get_header("Authorization") is None
        self.calls.append(request)
        if request.full_url.endswith("/api/v1/warrants"):
            assert request.method == "GET"
            return FakeResponse(self.products, 200)
        warrant_id = request.full_url.split("/warrants/", 1)[1].split("/", 1)[0]
        assert warrant_id in {product["id"] for product in self.products}
        if request.method == "GET":
            assert request.full_url.endswith("/deadline-listing-terms/current")
            if self.fail_current is not None:
                raise HTTPError(request.full_url, self.fail_current, "synthetic", None, None)
        else:
            assert request.method == "POST"
            assert request.full_url.endswith("/deadline-listing-terms/imports")
            if self.fail_import is not None:
                raise HTTPError(request.full_url, self.fail_import, "synthetic", None, None)
            assert request.data is not None
            payload = json.loads(request.data)
            assert set(payload) == {"document_base64"}
            content = base64.b64decode(payload["document_base64"], validate=True)
            if self.imported.get(warrant_id) != content:
                self.imported[warrant_id] = content
                self.revisions[warrant_id] = self.revisions.get(warrant_id, 0) + 1
        saved = warrant_id in self.imported
        return FakeResponse(
            {
                "warrant_id": warrant_id,
                "workspace_id": WORKSPACE,
                "status": self.api_status if saved else "MISSING",
                "revision_number": self.revisions.get(warrant_id, 0),
                "reasons": ["SYNTHETIC_DOCUMENT_ISSUE"] if self.api_status == "UNSUITABLE" else [],
                "verification": "USER_SUPPLIED_ORIGINAL_NOT_INDEPENDENT_VERIFICATION",
            },
            200 if request.method == "GET" else 201,
        )


@pytest.fixture
def api(script: ModuleType, monkeypatch: pytest.MonkeyPatch) -> SyntheticProductApi:
    synthetic = SyntheticProductApi()
    monkeypatch.setattr(script, "build_opener", synthetic.build_opener)
    return synthetic


def test_preview_reads_existing_products_and_evidence_without_mutation(
    script: ModuleType,
    api: SyntheticProductApi,
    disposable_source: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_original(disposable_source)
    (disposable_source / "unrelated.pdf").write_bytes(b"synthetic ignored")

    assert script.main([str(disposable_source)]) == 0
    assert [request.method for request in api.calls] == ["GET", "GET"]
    assert api.imported == {}
    assert isinstance(api.handlers[0], ProxyHandler) and api.handlers[0].proxies == {}
    assert isinstance(api.handlers[1], script._NoRedirect)
    output = capsys.readouterr().out
    assert "Vorschau: 1" in output and "Keine Schreiboperation" in output
    assert api.products[0]["id"] not in output


def test_all_preflight_finishes_before_any_write_and_original_bytes_survive_repeated_import(
    script: ModuleType,
    api: SyntheticProductApi,
    disposable_source: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first, second = write_original(disposable_source), write_original(
        disposable_source, second=True
    )

    assert script.main([str(disposable_source), "--apply"]) == 0
    assert [request.method for request in api.calls] == ["GET", "GET", "GET", "POST", "POST"]
    assert api.imported == {
        api.products[0]["id"]: first.read_bytes(),
        api.products[1]["id"]: second.read_bytes(),
    }
    assert script.main([str(disposable_source), "--apply"]) == 0
    assert list(api.revisions.values()) == [1, 1]
    output = capsys.readouterr().out
    assert "vorhandener Beleg wiederverwendet" in output
    assert "keine unabhängige Systemverifikation" in output
    assert "Ausstiegslisting" in output
    assert "vollständige B05/B20-Überwachung" in output


def test_existing_package_zip_names_read_without_extraction_or_running_embedded_code(
    script: ModuleType, api: SyntheticProductApi, disposable_source: Path
) -> None:
    package = disposable_source / "originals.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(f"sources/{ISIN}-xstu.html.txt", original())
        archive.writestr("sources/diagnostic.py", b"raise AssertionError('must not execute')")
        archive.writestr("sources/README.md", b"synthetic package")
    before = list(disposable_source.iterdir())

    assert script.main([str(package), "--apply"]) == 0
    assert list(disposable_source.iterdir()) == before
    assert list(api.imported.values()) == [original()]


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://192.168.1.3:8000",
        "http://example.invalid",
        "http://localhost.example.invalid",
        "http://localhost:8000/api/v1",
        "http://user:password@localhost:8000",
        "http://localhost:8000?workspace=other",
        "http://localhost:8000#fragment",
        "http://localhost:0",
        "http://localhost:99999",
        "http://local\nhost:8000",
        "http://[::2]:8000",
    ],
)
def test_nonlocal_or_ambiguous_api_url_rejected_before_http(
    script: ModuleType, api: SyntheticProductApi, disposable_source: Path, url: str
) -> None:
    write_original(disposable_source)
    assert script.main([str(disposable_source), "--api-url", url, "--apply"]) == 1
    assert api.calls == []


@pytest.mark.parametrize(
    "url", ["http://localhost:8000", "http://127.0.0.1:8000/", "http://[::1]:8000"]
)
def test_only_supported_loopback_origins(script: ModuleType, url: str) -> None:
    assert script.local_api_url(url) == url.rstrip("/")


def test_redirect_handler_refuses_all_redirects(script: ModuleType) -> None:
    with pytest.raises(script.ImportFailure, match="umgeleitet"):
        script._NoRedirect().redirect_request(None, None, None, None, None, "http://evil.invalid")


@pytest.mark.parametrize(
    "case", ["missing", "duplicate", "foreign_workspace", "wrong_wkn", "invalid_id"]
)
def test_entire_product_mapping_must_be_unambiguous_before_first_post(
    script: ModuleType, api: SyntheticProductApi, disposable_source: Path, case: str
) -> None:
    write_original(disposable_source)
    write_original(disposable_source, second=True)
    if case == "missing":
        api.products.pop()
    elif case == "duplicate":
        api.products.append(dict(api.products[-1]))
    elif case == "foreign_workspace":
        api.products[-1]["workspace_id"] = str(uuid4())
    elif case == "wrong_wkn":
        api.products[-1]["wkn"] = "OTHER1"
    else:
        api.products[-1]["id"] = "not-an-id"
    assert script.main([str(disposable_source), "--apply"]) == 1
    assert api.calls and all(request.method == "GET" for request in api.calls)
    assert api.imported == {}


@pytest.mark.parametrize("http_status", [401, 403, 404, 500])
def test_existing_api_access_and_installed_import_routes_required_before_mutation(
    script: ModuleType, api: SyntheticProductApi, disposable_source: Path, http_status: int
) -> None:
    write_original(disposable_source)
    api.fail_current = http_status
    assert script.main([str(disposable_source), "--apply"]) == 1
    assert api.imported == {}
    assert all(request.method == "GET" for request in api.calls)


def test_unavailable_document_is_reported_without_false_qualification(
    script: ModuleType,
    api: SyntheticProductApi,
    disposable_source: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_original(disposable_source)
    api.api_status = "UNSUITABLE"
    assert script.main([str(disposable_source), "--apply"]) == 2
    output = capsys.readouterr().out
    assert "SYNTHETIC_DOCUMENT_ISSUE" in output
    assert "mit offenen Belegproblemen: 1" in output


def test_api_failure_after_request_never_claims_success_or_retries_silently(
    script: ModuleType,
    api: SyntheticProductApi,
    disposable_source: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_original(disposable_source)
    api.fail_import = 500
    assert script.main([str(disposable_source), "--apply"]) == 1
    assert [request.method for request in api.calls] == ["GET", "GET", "POST"]
    output = capsys.readouterr().err
    assert "bestätigte Originalimporte: 0" in output
    assert "bereits gespeichert sein" in output


@pytest.mark.parametrize(
    "case",
    ["different_isin", "different_wkn", "duplicate_heading", "wrong_source", "script_identity"],
)
def test_file_identity_is_preflighted_before_any_http(
    script: ModuleType, api: SyntheticProductApi, disposable_source: Path, case: str
) -> None:
    content = original()
    if case == "different_isin":
        content = content.replace(ISIN.encode(), ISIN_SECOND.encode())
    elif case == "different_wkn":
        content = content.replace(b"WKN TEST12", b"WKN OTHER1")
    elif case == "duplicate_heading":
        content = content.replace(b"</body>", b"<h1>another heading</h1></body>")
    elif case == "wrong_source":
        content = content.replace(b"www.boerse-stuttgart.de", b"example.invalid")
    else:
        content = content.replace(f"ISIN {ISIN}".encode(), f"<script>ISIN {ISIN}</script>".encode())
    (disposable_source / f"{ISIN}-xstu.html").write_bytes(content)
    assert script.main([str(disposable_source), "--apply"]) == 1
    assert api.calls == []


@pytest.mark.parametrize(
    "member", ["../outside.txt", "/absolute.txt", "source/../outside.txt", "source\\outside.txt"]
)
def test_unsafe_zip_paths_block_entire_package_before_any_http(
    script: ModuleType, api: SyntheticProductApi, disposable_source: Path, member: str
) -> None:
    package = disposable_source / "originals.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(f"sources/{ISIN}-xstu.html.txt", original())
        archive.writestr(member, "synthetic")
    assert script.main([str(package), "--apply"]) == 1
    assert api.calls == []


def test_zip_symlink_duplicate_product_and_inflated_size_each_block_preflight(
    script: ModuleType,
    api: SyntheticProductApi,
    disposable_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for case in ("symlink", "duplicate", "too_large"):
        package = disposable_source / f"{case}.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr(f"sources/{ISIN}-xstu.html.txt", original())
            if case == "symlink":
                item = zipfile.ZipInfo("sources/symlink")
                item.create_system = 3
                item.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(item, "../elsewhere")
            elif case == "duplicate":
                archive.writestr(f"another/{ISIN}-xstu.html", original())
            else:
                monkeypatch.setattr(script, "MAX_DOCUMENT_BYTES", len(original()) - 1)
        assert script.main([str(package), "--apply"]) == 1
        assert api.calls == []


def test_directory_symlinks_and_duplicate_originals_are_not_followed_or_guessed(
    script: ModuleType, api: SyntheticProductApi, disposable_source: Path
) -> None:
    first = write_original(disposable_source)
    duplicate = disposable_source / f"{ISIN}-xstu.html.txt"
    duplicate.write_bytes(first.read_bytes())
    assert script.main([str(disposable_source), "--apply"]) == 1
    duplicate.unlink()
    duplicate.symlink_to(first)
    assert script.main([str(disposable_source), "--apply"]) == 1
    assert api.calls == []


def test_source_bytes_are_cached_before_apply_not_reopened_after_preflight(
    script: ModuleType,
    api: SyntheticProductApi,
    disposable_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = write_original(disposable_source)
    expected = path.read_bytes()
    prepare = script.prepare_imports

    def replace_source_after_preview(*args: Any) -> Any:
        plan = prepare(*args)
        path.write_bytes(b"changed synthetic source after preflight")
        return plan

    monkeypatch.setattr(script, "prepare_imports", replace_source_after_preview)
    assert script.main([str(disposable_source), "--apply"]) == 0
    assert list(api.imported.values()) == [expected]

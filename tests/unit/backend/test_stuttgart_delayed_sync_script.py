from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


def _load_script() -> ModuleType:
    root = Path(__file__).resolve().parents[3]
    path = root / "scripts" / "sync-stuttgart-delayed.py"
    spec = importlib.util.spec_from_file_location("sync_stuttgart_delayed", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_download_uses_index_filename_for_opaque_short_link() -> None:
    module = _load_script()
    html = """
    <tr>
      <td>XSTU-pretrade-20260908T1240.json.gz</td>
      <td>08.09.2026 12:40</td>
      <td><a href="https://ddl.service.boerse-stuttgart.de/s/Twmjkkjp">Herunterladen</a></td>
    </tr>
    """

    url, filename = module._official_download(html)

    assert url == "https://ddl.service.boerse-stuttgart.de/s/Twmjkkjp"
    assert filename == "XSTU-pretrade-20260908T1240.json.gz"


def test_official_download_rejects_non_official_host() -> None:
    module = _load_script()
    html = """
    <tr>
      <td>XSTU-pretrade-20260908T1240.json.gz</td>
      <td>08.09.2026 12:40</td>
      <td><a href="https://example.com/s/Twmjkkjp">Herunterladen</a></td>
    </tr>
    """

    with pytest.raises(RuntimeError, match="No official XSTU download entry"):
        module._official_download(html)


def test_validate_payload_accepts_nonempty_json_list() -> None:
    module = _load_script()
    content = gzip.compress(json.dumps([{"Isin": "DE000VH2LU21"}]).encode())

    module._validate_payload(content)


def test_validate_payload_rejects_empty_json_list() -> None:
    module = _load_script()
    content = gzip.compress(b"[]")

    with pytest.raises(RuntimeError, match="payload is empty"):
        module._validate_payload(content)


def test_validate_payload_rejects_empty_json_dict() -> None:
    module = _load_script()
    content = gzip.compress(b"{}")

    with pytest.raises(RuntimeError, match="payload is empty"):
        module._validate_payload(content)

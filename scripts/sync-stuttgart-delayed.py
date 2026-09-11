#!/usr/bin/env python3
"""Download the newest official XSTU delayed gzip into the local runtime cache."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

INDEX_URL = (
    "https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/"
    "mifir-ii-delayed-data/xstu-pre-trade/"
)
FILE_NAME_PATTERN = r"XSTU-pretrade-\d{8}T\d{4}\.json\.gz"
DOWNLOAD_ENTRY = re.compile(
    rf"(?P<filename>{FILE_NAME_PATTERN})[\s\S]{{0,2000}}?"
    r'href=["\'](?P<href>[^"\']*ddl\.service\.boerse-stuttgart\.de[^"\']*)["\']',
    re.IGNORECASE,
)
FILE_NAME = re.compile(rf"^{FILE_NAME_PATTERN}$")


def _get(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"User-Agent": "trading-workspace/1.0"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - hosts are validated below
        return response.read()


def _official_download(index_html: str) -> tuple[str, str]:
    match = DOWNLOAD_ENTRY.search(index_html)
    if match is None:
        raise RuntimeError("No official XSTU download entry found in Stuttgart index")

    filename = match.group("filename")
    if not FILE_NAME.fullmatch(filename):
        raise RuntimeError(f"Unexpected XSTU filename in Stuttgart index: {filename}")

    url = urljoin(INDEX_URL, match.group("href"))
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "ddl.service.boerse-stuttgart.de":
        raise RuntimeError("Unexpected Stuttgart delayed download host")
    return url, filename


def _validate_payload(content: bytes) -> None:
    try:
        payload = json.loads(gzip.decompress(content).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Downloaded XSTU payload is not valid UTF-8 JSON gzip") from exc
    if not isinstance(payload, (list, dict)):
        raise RuntimeError("Downloaded XSTU payload has an unsupported JSON root")
    if not payload:
        raise RuntimeError("Downloaded XSTU payload is empty; keeping last known good snapshot")


def _prune(directory: Path, keep: int) -> None:
    files = sorted(path for path in directory.glob("XSTU-pretrade-*.json.gz") if path.is_file())
    for path in files[:-keep]:
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="docker/stuttgart-data")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--keep", type=int, default=8)
    args = parser.parse_args()
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=True)

    index_html = _get(INDEX_URL, args.timeout).decode("utf-8")
    download_url, filename = _official_download(index_html)

    destination = directory / filename
    if destination.exists():
        print(f"Stuttgart delayed cache already current: {destination}")
        return 0

    content = _get(download_url, args.timeout)
    _validate_payload(content)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{filename}.", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    _prune(directory, max(args.keep, 1))
    print(f"Downloaded Stuttgart delayed payload: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

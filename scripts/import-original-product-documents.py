#!/usr/bin/env python3
"""Import supplied original Stuttgart HTML once through the local Product API.

The default is a read-only preview. --apply imports the unchanged bytes through
the existing owner, which alone qualifies dates and generates evidence revisions.
This helper does not fetch provider data, select an exit listing or activate rules.
It deliberately supports only the existing local workspace and loopback API.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import stat
import sys
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID

LOCAL_WORKSPACE = "00000000-0000-4000-8000-000000000001"
VERIFICATION = "USER_SUPPLIED_ORIGINAL_NOT_INDEPENDENT_VERIFICATION"
MAX_DOCUMENT_BYTES = 2_000_000
MAX_SOURCE_BYTES = 50_000_000
MAX_MEMBERS = 1_000
MAX_DOCUMENTS = 100
MAX_API_BYTES = 8_000_000
DOCUMENT_NAME = re.compile(r"([A-Z]{2}[A-Z0-9]{9}[0-9])-xstu\.html(?:\.txt)?")
VOID_TAGS = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)


class ImportFailure(Exception):
    """A bounded local validation or API failure; no provider fallback is allowed."""


@dataclass(frozen=True)
class OriginalDocument:
    name: str
    isin: str
    wkn: str
    content: bytes


@dataclass(frozen=True)
class PlannedImport:
    document: OriginalDocument
    warrant_id: str
    display_name: str
    prior_revision: int
    prior_status: str


def _display(value: str) -> str:
    """Keep untrusted filenames/names from inserting terminal controls or lines."""
    return " ".join("".join(char if char.isprintable() else " " for char in value).split())[:200]


class _IdentityParser(HTMLParser):
    """Identity-only preflight, not a second date qualification implementation."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, list[str] | None]] = [("root", None)]
        self.canonicals: list[str] = []
        self.headings: list[list[str]] = []
        self.titles: list[list[str]] = []
        self.nodes = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes += 1
        if self.nodes > 25_000 or len(self.stack) >= 64:
            raise ImportFailure("HTML-Struktur überschreitet die erlaubte Grenze.")
        attributes = dict(attrs)
        if tag == "link" and "canonical" in (attributes.get("rel") or "").casefold().split():
            self.canonicals.append(attributes.get("href") or "")
        if tag == "h1":
            parts: list[str] = []
            self.headings.append(parts)
            self.stack[-1] = (self.stack[-1][0], parts)
        capture: list[str] | None = [] if tag == "title" else None
        if capture is not None:
            self.titles.append(capture)
        if tag not in VOID_TAGS:
            self.stack.append((tag, capture))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in {"script", "style"} for tag, _ in self.stack):
            return
        for _, capture in self.stack:
            if capture is not None:
                capture.append(data)


def _document(name: str, content: bytes) -> OriginalDocument:
    match = DOCUMENT_NAME.fullmatch(PurePosixPath(name).name)
    if match is None or not 1 <= len(content) <= MAX_DOCUMENT_BYTES:
        raise ImportFailure(f"Unzulässige Originaldatei: {_display(name)}")
    isin = match.group(1)
    try:
        page = _IdentityParser()
        page.feed(content.decode("utf-8-sig"))
        page.close()
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise ImportFailure(f"HTML nicht eindeutig lesbar: {_display(name)}") from error
    if len(page.canonicals) != 1 or len(page.headings) != 1 or len(page.titles) != 1:
        raise ImportFailure(f"Original-Produktidentität nicht eindeutig: {_display(name)}")
    url = urlsplit(page.canonicals[0])
    path = re.fullmatch(
        r"/de-de/produkte/hebelprodukte/optionsscheine/stuttgart/([a-z0-9]{6})/", url.path
    )
    if (
        url.scheme != "https"
        or url.netloc != "www.boerse-stuttgart.de"
        or url.query
        or url.fragment
        or path is None
    ):
        raise ImportFailure(f"Kein unterstütztes Stuttgart-Original: {_display(name)}")
    wkn = path.group(1).upper()
    heading = " ".join(" ".join(page.headings[0]).split())
    title = " ".join(" ".join(page.titles[0]).split())
    if (
        set(re.findall(r"\bISIN\s*:?\s*([A-Z]{2}[A-Z0-9]{9}[0-9])\b", heading)) != {isin}
        or set(re.findall(r"\bWKN\s*:?\s*([A-Z0-9]{6})\b", heading)) != {wkn}
        or not title.endswith("Börse Stuttgart (XSTU)")
        or re.search(rf"\b{wkn}\b", title) is None
    ):
        raise ImportFailure(f"Dateiname und Original-Produktidentität widersprechen sich: {isin}")
    return OriginalDocument(name, isin, wkn, content)


def _read_file(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ImportFailure("Originalquelle muss eine reguläre Datei sein.")
        content = handle.read(MAX_DOCUMENT_BYTES + 1)
    return content


def _directory_documents(source: Path) -> list[OriginalDocument]:
    documents: list[OriginalDocument] = []
    members = 0
    total_bytes = 0
    for directory, directories, files in os.walk(source, followlinks=False):
        relative = Path(directory).relative_to(source)
        if len(relative.parts) > 4:
            raise ImportFailure("Quellenverzeichnis ist zu tief verschachtelt.")
        for name in sorted(directories + files):
            members += 1
            if members > MAX_MEMBERS:
                raise ImportFailure("Quellenverzeichnis enthält zu viele Einträge.")
            path = Path(directory) / name
            if path.is_symlink() or not path.resolve().is_relative_to(source):
                raise ImportFailure("Verknüpfungen in der Originalquelle sind nicht zulässig.")
            if DOCUMENT_NAME.fullmatch(name):
                document = _document(str(path.relative_to(source)), _read_file(path))
                total_bytes += len(document.content)
                if len(documents) >= MAX_DOCUMENTS or total_bytes > MAX_SOURCE_BYTES:
                    raise ImportFailure(
                        "Quellenverzeichnis enthält zu viele oder zu große Originale."
                    )
                documents.append(document)
    return documents


def _zip_documents(source: Path) -> list[OriginalDocument]:
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ImportFailure("Quellenarchiv überschreitet die erlaubte Größe.")
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS or sum(item.file_size for item in members) > MAX_SOURCE_BYTES:
            raise ImportFailure("Quellenarchiv überschreitet die erlaubten Grenzen.")
        names: set[str] = set()
        candidates: list[zipfile.ZipInfo] = []
        for item in members:
            path = PurePosixPath(item.filename)
            mode = stat.S_IFMT(item.external_attr >> 16)
            if (
                len(item.filename) > 512
                or item.filename != item.orig_filename
                or "\\" in item.filename
                or ":" in item.filename
                or path.is_absolute()
                or any(part in {"", ".", ".."} for part in item.filename.rstrip("/").split("/"))
                or item.filename.casefold() in names
                or item.flag_bits & 1
                or mode not in {0, stat.S_IFREG, stat.S_IFDIR}
                or (mode == stat.S_IFDIR and not item.is_dir())
                or item.file_size < 0
                or item.file_size > max(1, item.compress_size) * 1_000
            ):
                raise ImportFailure("Quellenarchiv enthält mehrdeutige oder unzulässige Einträge.")
            names.add(item.filename.casefold())
            if DOCUMENT_NAME.fullmatch(path.name):
                if item.is_dir() or item.file_size > MAX_DOCUMENT_BYTES:
                    raise ImportFailure("Originaldatei im Archiv überschreitet die erlaubte Größe.")
                candidates.append(item)
        if len(candidates) > MAX_DOCUMENTS:
            raise ImportFailure("Quellenarchiv enthält zu viele Originaldokumente.")
        documents = []
        for item in candidates:
            with archive.open(item) as handle:
                content = handle.read(MAX_DOCUMENT_BYTES + 1)
            documents.append(_document(item.filename, content))
        return documents


def read_documents(source: Path) -> tuple[OriginalDocument, ...]:
    if source.is_symlink():
        raise ImportFailure("Die Originalquelle darf keine Verknüpfung sein.")
    source = source.resolve(strict=True)
    if source.is_dir():
        documents = _directory_documents(source)
    elif source.suffix.casefold() == ".zip":
        documents = _zip_documents(source)
    else:
        documents = [_document(source.name, _read_file(source))]
    if not documents:
        raise ImportFailure("Keine Originaldateien nach Muster <ISIN>-xstu.html[.txt] gefunden.")
    if (
        len(documents) > MAX_DOCUMENTS
        or sum(len(document.content) for document in documents) > MAX_SOURCE_BYTES
    ):
        raise ImportFailure("Die Originaldokumente überschreiten die erlaubten Grenzen.")
    if len({document.isin for document in documents}) != len(documents):
        raise ImportFailure(
            "Mehrere Originaldateien für dieselbe ISIN; zuerst eine Quelle auswählen."
        )
    return tuple(sorted(documents, key=lambda document: document.isin))


def local_api_url(value: str) -> str:
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError as error:
        raise ImportFailure("Ungültige lokale API-Adresse.") from error
    if (
        url.scheme != "http"
        or any(char.isspace() or not char.isprintable() for char in value)
        or url.hostname not in {"localhost", "127.0.0.1", "::1"}
        or url.username is not None
        or url.password is not None
        or url.path not in {"", "/"}
        or url.query
        or url.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ImportFailure(
            "Nur die lokale HTTP-API auf localhost, 127.0.0.1 oder ::1 ist erlaubt."
        )
    return value.rstrip("/")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        raise ImportFailure("Die lokale API hat umgeleitet; Import abgebrochen.")


class LocalProductApi:
    def __init__(self, origin: str) -> None:
        self.origin = local_api_url(origin)
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())

    def request(self, path: str, *, payload: dict[str, str] | None = None) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.origin + path,
            data=data,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="GET" if data is None else "POST",
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                if response.status != (200 if data is None else 201):
                    raise ImportFailure("Unerwarteter Antwortstatus der lokalen API.")
                content = response.read(MAX_API_BYTES + 1)
                if len(content) > MAX_API_BYTES:
                    raise ImportFailure("Antwort der lokalen API überschreitet die erlaubte Größe.")
                return json.loads(content)
        except HTTPError as error:
            if error.code in {401, 403}:
                raise ImportFailure(
                    "Lokale API verweigert den Zugriff; keine Umgehung versucht."
                ) from error
            if error.code == 404:
                raise ImportFailure(
                    "Import-API oder Produkt fehlt. "
                    "Zuerst die freigegebene Programmversion installieren."
                ) from error
            raise ImportFailure(
                f"Lokale API meldet HTTP {error.code}; Import abgebrochen."
            ) from error
        except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ImportFailure("Lokale API nicht erreichbar oder Antwort nicht lesbar.") from error


def _evidence(response: Any, warrant_id: str) -> tuple[str, int, tuple[str, ...]]:
    if not isinstance(response, dict):
        raise ImportFailure("Unerwartete Belegantwort der lokalen API.")
    status, revision = response.get("status"), response.get("revision_number")
    reasons = response.get("reasons")
    if (
        response.get("warrant_id") != warrant_id
        or response.get("workspace_id") != LOCAL_WORKSPACE
        or not isinstance(status, str)
        or status not in {"AVAILABLE", "MISSING", "UNSUITABLE"}
        or type(revision) is not int
        or revision < 0
        or not isinstance(reasons, list)
        or not all(isinstance(reason, str) for reason in reasons)
        or response.get("verification") != VERIFICATION
    ):
        raise ImportFailure("Die Belegantwort passt nicht zum lokalen Produkt-/Quellenvertrag.")
    return status, revision, tuple(reasons)


def prepare_imports(
    api: LocalProductApi, documents: tuple[OriginalDocument, ...]
) -> list[PlannedImport]:
    response = api.request("/api/v1/warrants")
    if not isinstance(response, list) or not all(isinstance(row, dict) for row in response):
        raise ImportFailure("Unerwartete Produktliste der lokalen API.")
    plans = []
    for document in documents:
        matches = [row for row in response if row.get("isin") == document.isin]
        if len(matches) != 1:
            raise ImportFailure(f"Keine eindeutige gespeicherte Produktzuordnung: {document.isin}")
        warrant = matches[0]
        try:
            warrant_id = str(UUID(warrant["id"]))
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise ImportFailure("Gespeicherte Produktidentität ist ungültig.") from error
        if (
            warrant.get("workspace_id") != LOCAL_WORKSPACE
            or warrant.get("wkn") not in (None, "", document.wkn)
            or not isinstance(warrant.get("display_name"), str)
        ):
            raise ImportFailure(f"Gespeichertes Produkt widerspricht dem Original: {document.isin}")
        current = api.request(f"/api/v1/warrants/{warrant_id}/deadline-listing-terms/current")
        status, revision, _ = _evidence(current, warrant_id)
        plans.append(PlannedImport(document, warrant_id, warrant["display_name"], revision, status))
    if len({plan.warrant_id for plan in plans}) != len(plans):
        raise ImportFailure(
            "Mehrdeutige gespeicherte Produktzuordnung; keine Originale importiert."
        )
    return plans


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", type=Path, help="Originaldatei, Verzeichnis oder vorhandenes Quellen-ZIP"
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="Lokale Backend-Adresse")
    parser.add_argument(
        "--apply", action="store_true", help="Geprüfte Originaldateien einmalig importieren"
    )
    args = parser.parse_args(argv)
    imported = 0
    try:
        api = LocalProductApi(args.api_url)
        documents = read_documents(args.source)
        plans = prepare_imports(api, documents)
        print(
            f"{'Import' if args.apply else 'Vorschau'}: "
            f"{len(plans)} vorhandene Produkte eindeutig zugeordnet."
        )
        for plan in plans:
            print(
                f"  {plan.document.isin} | {_display(plan.display_name)} | "
                f"{len(plan.document.content)} Bytes | bisher {plan.prior_status}, "
                f"Revision {plan.prior_revision}"
            )
        if not args.apply:
            print(
                "Keine Schreiboperation ausgeführt. "
                "--apply importiert diese unveränderten Originaldateien."
            )
            return 0
        unavailable = 0
        for plan in plans:
            response = api.request(
                f"/api/v1/warrants/{plan.warrant_id}/deadline-listing-terms/imports",
                payload={
                    "document_base64": base64.b64encode(plan.document.content).decode("ascii")
                },
            )
            status, revision, reasons = _evidence(response, plan.warrant_id)
            imported += 1
            unchanged = (
                " (vorhandener Beleg wiederverwendet)" if revision == plan.prior_revision else ""
            )
            print(f"  {plan.document.isin}: {status}, Revision {revision}{unchanged}")
            if status != "AVAILABLE":
                unavailable += 1
                print(f"    Offene Belegprobleme: {_display(', '.join(reasons))}")
        print(
            f"Originaldateien verarbeitet: {imported}; "
            f"davon mit offenen Belegproblemen: {unavailable}."
        )
        print(
            "Die Dateien bleiben nutzerbereitgestellte Originale, "
            "keine unabhängige Systemverifikation."
        )
        print(
            "Das feste Ausstiegslisting in der Positionsansicht ausdrücklich wählen; "
            "Kalenderabdeckung beachten."
        )
        print(
            "Keine B58-Qualifikation, vollständige B05/B20-Überwachung "
            "oder Aktivierung dadurch bestätigt."
        )
        return 2 if unavailable else 0
    except (ImportFailure, OSError, ValueError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"Abgebrochen: {_display(str(error))}", file=sys.stderr)
        if args.apply:
            print(
                f"Erfolgreich bestätigte Originalimporte: {imported}. "
                "Ein zuvor abgesendeter Import kann bei Antwortabbruch bereits gespeichert sein; "
                "gleicher Wiederholungsimport bleibt dedupliziert.",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

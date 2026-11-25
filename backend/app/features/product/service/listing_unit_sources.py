"""Bounded local originals qualification; no HTTP, database or caller trust flags."""

import base64
import binascii
import gzip
import hashlib
import re
from dataclasses import asdict
from datetime import datetime
from io import TextIOWrapper
from typing import BinaryIO, NoReturn

from app.features.product.domain.listing_unit_evidence import (
    ListingUnitPretradeEvidence,
    ListingUnitRuleEvidence,
    ListingUnitRuleOriginal,
    ListingUnitRuleSet,
    QualifiedGettexListingSource,
)
from app.features.product.domain.price_scale_evidence import aware, reference, sha256_text
from app.features.product.persistence.price_scale_evidence import fingerprint
from app.features.product.service.listing_unit_rules import (
    SUPPORTED_RULE_SETS as SUPPORTED_RULE_SETS,
)
from app.providers.gettex_delayed.parser import (
    GettexPayloadError,
    GettexQuoteRow,
    parse_file_window,
    parse_quote_row,
    scan_gzip_quote_batch,
)

MAX_RULE_DOCUMENT_BYTES = 4_000_000
MAX_RULE_DOCUMENTS_BYTES = 16_000_000
MAX_PRETRADE_BYTES = 1_073_741_824
MAX_TARGET_ROW_BYTES = 4096
RULE_ROLES = frozenset(
    {"EXCHANGE_RULES", "OPEN_MARKET_RULES", "EXECUTION_RULES", "PRODUCT_CLASSIFICATION"}
)


class ListingUnitSourceError(ValueError):
    """Only stable, bounded codes leave the local originals boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> NoReturn:
    raise ListingUnitSourceError(code)


def _clock(value: datetime, known_at: datetime) -> None:
    if not aware(value) or value > known_at:
        _fail("LISTING_UNIT_SOURCE_CLOCK_INVALID")


def _rule_set_valid(spec: ListingUnitRuleSet, known_at: datetime) -> None:
    if not aware(known_at) or not aware(spec.observed_at):
        _fail("LISTING_UNIT_RULE_CLOCK_INVALID")
    if spec.observed_at > known_at:
        _fail("LISTING_UNIT_RULE_NOT_YET_KNOWN")
    if spec.effective_from is not None and not aware(spec.effective_from):
        _fail("LISTING_UNIT_RULE_CLOCK_INVALID")
    if (
        not re.fullmatch(r"[A-Za-z0-9_.:-]{3,128}", spec.version)
        or len(spec.documents) != len(RULE_ROLES)
        or {item.role for item in spec.documents} != RULE_ROLES
        or spec.venue_mic != "MUND"
        or spec.currency != "EUR"
        or spec.product_class != "CALL_WARRANT_ON_EQUITY"
    ):
        _fail("LISTING_UNIT_RULE_CONTRACT_INVALID")
    for document in spec.documents:
        try:
            sha256_text(document.document_sha256)
            reference(document.source_reference, 2000)
        except ValueError as error:
            raise ListingUnitSourceError("LISTING_UNIT_RULE_CONTRACT_INVALID") from error
        if document.media_type not in {"application/pdf", "text/html"}:
            _fail("LISTING_UNIT_RULE_CONTRACT_INVALID")


def qualified_rule_set(
    originals: tuple[ListingUnitRuleOriginal, ...],
    *,
    known_at: datetime,
    registry: tuple[ListingUnitRuleSet, ...],
) -> tuple[ListingUnitRuleSet, tuple[ListingUnitRuleEvidence, ...]]:
    if not registry:
        _fail("LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED")
    if not aware(known_at):
        _fail("LISTING_UNIT_SOURCE_CLOCK_INVALID")
    if len(originals) != len(RULE_ROLES) or {item.role for item in originals} != RULE_ROLES:
        _fail("LISTING_UNIT_RULE_ORIGINALS_INCOMPLETE")
    if sum(len(item.document) for item in originals) > MAX_RULE_DOCUMENTS_BYTES:
        _fail("LISTING_UNIT_RULE_ORIGINALS_TOO_LARGE")
    hashes: dict[str, str] = {}
    for item in originals:
        if not 0 < len(item.document) <= MAX_RULE_DOCUMENT_BYTES:
            _fail("LISTING_UNIT_RULE_ORIGINAL_SIZE_INVALID")
        if (
            not 3 <= len(item.filename) <= 255
            or any(character in item.filename for character in ("/", "\\", "\x00"))
            or item.media_type not in {"application/pdf", "text/html"}
            or (item.media_type == "application/pdf" and not item.document.startswith(b"%PDF-"))
        ):
            _fail("LISTING_UNIT_RULE_ORIGINAL_INVALID")
        if item.retrieved_at is not None:
            _clock(item.retrieved_at, known_at)
        hashes[item.role] = hashlib.sha256(item.document).hexdigest()
    matches = [
        spec
        for spec in registry
        if len(spec.documents) == len(originals)
        and {item.role: item.document_sha256 for item in spec.documents} == hashes
    ]
    if len(matches) != 1:
        _fail("LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED")
    spec = matches[0]
    _rule_set_valid(spec, known_at)
    documents = {item.role: item for item in spec.documents}
    evidence = []
    for item in sorted(originals, key=lambda value: value.role):
        expected = documents[item.role]
        if item.media_type != expected.media_type:
            _fail("LISTING_UNIT_RULE_MEDIA_TYPE_MISMATCH")
        evidence.append(
            ListingUnitRuleEvidence(
                item.role,
                item.filename,
                item.media_type,
                expected.source_reference,
                hashes[item.role],
                base64.b64encode(item.document).decode("ascii"),
                item.retrieved_at,
            )
        )
    return spec, tuple(evidence)


def _file_digest(source: BinaryIO) -> tuple[str, int]:
    source.seek(0)
    digest = hashlib.sha256()
    size = 0
    while chunk := source.read(1_048_576):
        size += len(chunk)
        if size > MAX_PRETRADE_BYTES:
            _fail("LISTING_UNIT_PRETRADE_TOO_LARGE")
        digest.update(chunk)
    if size == 0:
        _fail("LISTING_UNIT_PRETRADE_EMPTY")
    source.seek(0)
    return digest.hexdigest(), size


def _original_target_row(source: BinaryIO, file_name: str, target: GettexQuoteRow) -> str:
    """Retain an unchanged CSV record after the existing parser checked the full file."""
    source.seek(0)
    window = parse_file_window(file_name)
    with gzip.GzipFile(fileobj=source, mode="rb") as compressed:
        text = TextIOWrapper(compressed, encoding="utf-8", newline="")
        for line in text:
            if line.partition(",")[0].strip().upper() != target.isin:
                continue
            original = line.rstrip("\r\n")
            if len(original.encode("utf-8")) > MAX_TARGET_ROW_BYTES:
                _fail("LISTING_UNIT_TARGET_ROW_TOO_LARGE")
            if parse_quote_row(original, window=window) == target:
                return original
    _fail("LISTING_UNIT_TARGET_ROW_NOT_REPRODUCIBLE")


class _StreamQualifiedSource(QualifiedGettexListingSource):
    """Internal capability produced only after scanning, not by JSON DTO validation."""

    __slots__ = ()


def require_stream_qualified(source: QualifiedGettexListingSource) -> None:
    if not isinstance(source, _StreamQualifiedSource):
        _fail("LISTING_UNIT_COMPLETE_SOURCE_SCAN_REQUIRED")


def source_fingerprint(source: QualifiedGettexListingSource) -> str:
    material = asdict(source)
    # A repeated qualification clock is not a new original or new source fact.
    material.pop("qualified_at")
    material.pop("fingerprint")
    return fingerprint(material)


def qualify_gettex_listing_source(
    *,
    source: BinaryIO,
    file_name: str,
    target_isin: str,
    rules: tuple[ListingUnitRuleOriginal, ...],
    known_at: datetime,
    retrieved_at: datetime | None = None,
    registry: tuple[ListingUnitRuleSet, ...] | None = None,
) -> QualifiedGettexListingSource:
    """Verify the complete local original before any Product mutation is possible.

    The target row is evidence of product/listing membership, never an imported
    current price. Its original event, download and qualification clocks differ.
    """
    spec, originals = qualified_rule_set(
        rules, known_at=known_at, registry=SUPPORTED_RULE_SETS if registry is None else registry
    )
    if not re.fullmatch(r"[A-Z0-9]{12}", target_isin) or not source.seekable():
        _fail("LISTING_UNIT_PRETRADE_INPUT_INVALID")
    if retrieved_at is not None:
        _clock(retrieved_at, known_at)
    try:
        window = parse_file_window(file_name)
        if window.mic != spec.venue_mic or window.ends_at > known_at:
            _fail("LISTING_UNIT_PRETRADE_WINDOW_UNSUITABLE")
        if retrieved_at is not None and retrieved_at < window.ends_at:
            _fail("LISTING_UNIT_PRETRADE_RECEIPT_BEFORE_WINDOW_END")
        digest, size = _file_digest(source)
        batch = scan_gzip_quote_batch(source, file_name=file_name, tracked_isins={target_isin})
        if target_isin in batch.errors:
            _fail(batch.errors[target_isin])
        target = batch.quotes.get(target_isin)
        if target is None:
            _fail("LISTING_UNIT_TARGET_NOT_IN_PRETRADE_FILE")
        if target.currency != spec.currency or target.mic != spec.venue_mic:
            _fail("LISTING_UNIT_TARGET_ROUTE_MISMATCH")
        original = _original_target_row(source, file_name, target)
        if _file_digest(source) != (digest, size):
            _fail("LISTING_UNIT_PRETRADE_CHANGED_DURING_SCAN")
    except (GettexPayloadError, OSError, UnicodeError, EOFError) as error:
        raise ListingUnitSourceError("LISTING_UNIT_PRETRADE_INVALID") from error
    pretrade = ListingUnitPretradeEvidence(
        file_name,
        digest,
        size,
        window.starts_at,
        window.ends_at,
        original,
        hashlib.sha256(original.encode("utf-8")).hexdigest(),
        target.isin,
        target.mic,
        target.currency,
        target.observed_at,
        retrieved_at,
    )
    result = QualifiedGettexListingSource(
        spec.version, fingerprint(asdict(spec)), originals, pretrade, known_at, ""
    )
    return _StreamQualifiedSource(
        result.rule_set_version,
        result.rule_set_fingerprint,
        result.rule_originals,
        result.pretrade,
        result.qualified_at,
        source_fingerprint(result),
    )


def validate_qualified_source(
    source: QualifiedGettexListingSource,
    *,
    known_at: datetime,
    registry: tuple[ListingUnitRuleSet, ...],
) -> ListingUnitRuleSet:
    """Revalidate saved minimal facts and every original; no previous-good fallback."""
    try:
        if len(source.rule_originals) != len(RULE_ROLES) or any(
            len(item.document_base64) > ((MAX_RULE_DOCUMENT_BYTES + 2) // 3) * 4
            for item in source.rule_originals
        ):
            _fail("LISTING_UNIT_RULE_ORIGINALS_TOO_LARGE")
        originals = tuple(
            ListingUnitRuleOriginal(
                item.role,
                item.filename,
                item.media_type,
                base64.b64decode(item.document_base64, validate=True),
                item.retrieved_at,
            )
            for item in source.rule_originals
        )
        spec, evidence = qualified_rule_set(originals, known_at=known_at, registry=registry)
        _clock(source.qualified_at, known_at)
        pretrade = source.pretrade
        window = parse_file_window(pretrade.file_name)
        row = parse_quote_row(pretrade.original_row, window=window)
        sha256_text(pretrade.file_sha256)
        if (
            source.rule_set_version != spec.version
            or source.rule_set_fingerprint != fingerprint(asdict(spec))
            or source.rule_originals != evidence
            or source.fingerprint != source_fingerprint(source)
            or not 0 < pretrade.file_bytes <= MAX_PRETRADE_BYTES
            or len(pretrade.original_row.encode("utf-8")) > MAX_TARGET_ROW_BYTES
            or pretrade.row_sha256 != hashlib.sha256(pretrade.original_row.encode()).hexdigest()
            or pretrade.window_starts_at != window.starts_at
            or pretrade.window_ends_at != window.ends_at
            or pretrade.isin != row.isin
            or pretrade.venue_mic != row.mic
            or pretrade.venue_mic != spec.venue_mic
            or pretrade.currency != row.currency
            or pretrade.currency != spec.currency
            or pretrade.observed_at != row.observed_at
            or pretrade.window_ends_at > source.qualified_at
            or pretrade.parser_version != "gettex-delayed-pretrade-parser-v1"
            or pretrade.verification != "COMPLETE_GZIP_SCAN_WITH_CRC_AND_EXACT_TARGET_ROW"
        ):
            _fail("LISTING_UNIT_SOURCE_INTEGRITY_INVALID")
        if pretrade.retrieved_at is not None:
            _clock(pretrade.retrieved_at, source.qualified_at)
            if pretrade.retrieved_at < pretrade.window_ends_at:
                _fail("LISTING_UNIT_SOURCE_INTEGRITY_INVALID")
        return spec
    except ListingUnitSourceError:
        raise
    except (ValueError, TypeError, AttributeError, binascii.Error, UnicodeError) as error:
        raise ListingUnitSourceError("LISTING_UNIT_SOURCE_INTEGRITY_INVALID") from error

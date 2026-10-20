"""Verifiable issuer route evidence; never infer quote dates or stream identifiers."""

import re
from datetime import UTC, date, datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from app.features.market.contracts import is_canonical_isin

VERSION = "ISSUER_PRODUCT_PAGE_V1"
SITES = {
    "JPMORGAN": ("www.jpmorgan-zertifikate.de", "/zertifikate-detail/", "staticgrid", "quotetime"),
    "MORGAN_STANLEY": (
        "zertifikate.morganstanley.com",
        "/produktdetails/",
        "instruments",
        "lastquotetimestamp",
    ),
}


def product_url(provider: str, isin: str) -> str:
    if provider not in SITES or not is_canonical_isin(isin):
        raise ValueError("ISSUER_INVALID_PRODUCT_REQUEST")
    host, path, _, _ = SITES[provider]
    return f"https://{host}{path}{isin.lower() if provider == 'MORGAN_STANLEY' else isin}"


def allowed_product_url(url: str, provider: str, isin: str) -> bool:
    expected = urlsplit(product_url(provider, isin))
    actual = urlsplit(url)
    hosts = {expected.hostname}
    if provider == "JPMORGAN":
        hosts.add("jpmorgan-zertifikate.de")
    return (
        actual.scheme == "https"
        and actual.netloc in hosts
        and actual.path.rstrip("/").lower() == expected.path.lower()
        and not actual.query
        and not actual.fragment
    )


def evidence_stream_id(
    evidence: object,
    *,
    provider: str,
    isin: str,
    currency: str,
    workspace_id: str,
    warrant_id: str,
    warrant_version: int,
    listing_id: str,
    listing_version: int,
    mapping_version: int,
    today: date | None = None,
) -> str | None:
    if not isinstance(evidence, dict):
        return None
    if evidence.get("acquisition_mode", "PUBLIC_HTTP") not in {"PUBLIC_HTTP", "RENDERED_DOM"}:
        return None
    expected = {
        "schema_version": VERSION,
        "provider": provider,
        "isin": isin,
        "currency": currency,
        "workspace_id": workspace_id,
        "warrant_id": warrant_id,
        "warrant_version": warrant_version,
        "listing_id": listing_id,
        "listing_version": listing_version,
        "mapping_version": mapping_version,
        "product_type": "Optionsschein",
    }
    if any(evidence.get(key) != value for key, value in expected.items()) or currency != "EUR":
        return None
    try:
        if not allowed_product_url(evidence["source_url"], provider, isin):
            return None
        if not re.fullmatch(r"[a-f0-9]{64}", evidence["source_sha256"]):
            return None
        stream_id = evidence["stream_id"]
        if not isinstance(stream_id, str) or not re.fullmatch(
            r"X[A-Z0-9]{1,20}" + re.escape(isin), stream_id
        ):
            return None
        received = datetime.fromisoformat(evidence["verified_at"])
        expiry = date.fromisoformat(evidence["valid_through"])
        current = today or datetime.now(ZoneInfo("Europe/Berlin")).date()
        if received.utcoffset() is None or received > datetime.now(UTC) or expiry < current:
            return None
        return stream_id
    except (ValueError, TypeError, KeyError, AttributeError):
        return None

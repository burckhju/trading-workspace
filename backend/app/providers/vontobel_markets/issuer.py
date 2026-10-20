"""Issuer labels select a probe, never authorize or identify a quote."""

import re
import unicodedata


def supports_issuer_probe(legal_name: str | None) -> bool:
    """Recognize a bounded abbreviation without changing issuer master data.

    Every candidate still needs the existing exact ISIN/WKN/currency/payload
    verification. Substrings such as NotVontobel and arbitrary VONT prefixes
    are deliberately not accepted.
    """
    tokens = tuple(
        re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", legal_name or "").casefold())
    )
    return "vontobel" in tokens or tokens == ("vont", "finl")

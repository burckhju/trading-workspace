"""Strict parser primitives for the official gettex delayed pre-trade files."""

from app.providers.gettex_delayed.parser import (
    GettexFileWindow,
    GettexPayloadError,
    GettexQuoteBatch,
    GettexQuoteRow,
    parse_file_window,
    parse_quote_row,
    scan_gzip_quote_batch,
    scan_gzip_quotes,
)

__all__ = [
    "GettexFileWindow",
    "GettexPayloadError",
    "GettexQuoteBatch",
    "GettexQuoteRow",
    "parse_file_window",
    "parse_quote_row",
    "scan_gzip_quote_batch",
    "scan_gzip_quotes",
]

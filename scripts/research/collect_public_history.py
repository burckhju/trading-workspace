"""Read-only public historical-data acquisition, independent of trading runtime.

No private recommendations, PDFs, positions, tokens, or .env files are read.
Unchanged provider payloads and hashes are returned for a separate local review.
A successful HTTP response is NOT a certified backtest or identity verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MAX_BYTES = 20_000_000
MAX_SYMBOLS = 150
ALLOWED_HOSTS = frozenset({"query1.finance.yahoo.com", "www.ecb.europa.eu"})


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate_symbols(value: Any) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SYMBOLS:
        raise ValueError("Expected 1..150 public ticker identifiers")
    if any(not isinstance(s, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.^=\-]{0,23}", s) for s in value):
        raise ValueError("Invalid ticker identifier")
    if len(set(value)) != len(value):
        raise ValueError("Duplicate ticker identifiers")
    return sorted(value)


def chart_url(symbol: str, start: str, end: str) -> str:
    validate_symbols([symbol])
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or last >= datetime.now(timezone.utc).date():
        raise ValueError("Use a past, completed-day cutoff")
    args = {"period1": int(datetime.combine(first, datetime.min.time(), timezone.utc).timestamp()),
            "period2": int(datetime.combine(last + timedelta(days=1), datetime.min.time(), timezone.utc).timestamp()),
            "interval": "1d", "events": "div,splits", "includeAdjustedClose": "true"}
    return "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?" + urllib.parse.urlencode(args)


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Redirect outside the public provider allowlist")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_payload(body: bytes, kind: str, symbol: str = "") -> dict[str, Any]:
    if kind == "ecb":
        root = ET.fromstring(body)
        days = [e.attrib["time"] for e in root.iter() if "time" in e.attrib]
        if not days:
            raise ValueError("Missing ECB dated observations")
        return {"observation_days": len(days), "first_date": min(days), "last_date": max(days)}
    obj = json.loads(body)
    chart = obj.get("chart", {})
    if chart.get("error") or not chart.get("result"):
        raise ValueError("Provider chart error or missing result")
    result = chart["result"][0]
    times = result.get("timestamp", [])
    if not times:
        raise ValueError("No price timestamps")
    if times != sorted(set(times)):
        raise ValueError("Duplicate or unsorted timestamps")
    quote = result["indicators"]["quote"][0]
    if any(len(quote.get(k, [])) != len(times) for k in ("open", "high", "low", "close", "volume")):
        raise ValueError("Misaligned provider arrays")
    meta = result["meta"]
    if meta.get("symbol", "").upper() != symbol.upper():
        raise ValueError("Provider symbol differs from request")
    return {"records": len(times), "provider_symbol": meta.get("symbol"),
            "currency": meta.get("currency"), "exchange": meta.get("exchangeName"),
            "exchange_timezone": meta.get("exchangeTimezoneName"),
            "first_timestamp": min(times), "last_timestamp": max(times),
            "split_events": len(result.get("events", {}).get("splits", {})),
            "dividend_events": len(result.get("events", {}).get("dividends", {})),
            "quality": "RAW_FETCH_ONLY_REVIEW_REQUIRED"}


def fetch(url: str, path: Path, kind: str, symbol: str = "", *, opener=None, sleeper=time.sleep) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("URL is not an allowed public provider")
    record_path = path.with_suffix(path.suffix + ".meta.json")
    if path.exists() and record_path.exists():
        old = json.loads(record_path.read_text(encoding="utf-8"))
        data = path.read_bytes()
        if old.get("status") == "FETCHED" and old.get("url") == url and old.get("sha256") == digest(data):
            validate_payload(data, kind, symbol)
            return {**old, "cache_hit": True}
    opener = opener or urllib.request.build_opener(SafeRedirect())
    record: dict[str, Any] = {"symbol": symbol, "kind": kind, "url": url, "started_at": stamp(), "attempts": [], "status": "FAILED"}
    for attempt in range(1, 3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "TradingWorkspaceResearch/0.1", "Accept": "application/json, application/xml;q=0.9"})
            with opener.open(request, timeout=20) as response:
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise ValueError("Provider response exceeds size bound")
                if response.status != 200:
                    raise ValueError("Unexpected HTTP status")
                summary = validate_payload(body, kind, symbol)
                record["attempts"].append({"attempt": attempt, "http_status": response.status})
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(path.suffix + ".tmp")
            temp.write_bytes(body)
            temp.replace(path)
            record.update(status="FETCHED", retrieved_at=stamp(), sha256=digest(body), bytes=len(body), summary=summary, cache_hit=False)
            write_json(record_path, record)
            return record
        except urllib.error.HTTPError as exc:
            record["attempts"].append({"attempt": attempt, "http_status": exc.code})
            record["error"] = "HTTP_" + str(exc.code)
            if exc.code in (401, 403, 404) or (exc.code != 429 and exc.code < 500):
                break
            if attempt < 2:
                retry = exc.headers.get("Retry-After", "10") if exc.headers else "10"
                if not retry.isdigit() or int(retry) > 30:
                    break
                sleeper(max(1, int(retry)))
        except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
            record["error"] = type(exc).__name__
            record["attempts"].append({"attempt": attempt, "exception": type(exc).__name__})
            if attempt < 2:
                sleeper(2)
    record["finished_at"] = stamp()
    write_json(record_path, record)
    return record


def collect(symbols: list[str], start: str, end: str, out: Path, *, spacing: float = 1.0) -> dict[str, Any]:
    symbols = validate_symbols(symbols)
    if spacing < 0.5:
        raise ValueError("Use a bounded, non-aggressive request cadence")
    for s in symbols:
        chart_url(s, start, end)
    manifest: dict[str, Any] = {"schema_version": "public-history-v1", "start": start, "end": end, "started_at": stamp(), "records": [], "symbols": symbols,
                              "scope": "public_quotes_only_no_private_recommendations_no_trading"}
    failures = 0
    for symbol in symbols:
        url = chart_url(symbol, start, end)
        if failures >= 3:
            rec = {"symbol": symbol, "kind": "yahoo", "status": "DEFERRED_PROVIDER_ERRORS", "url": url}
        else:
            rec = fetch(url, out / "raw" / (symbol + ".json"), "yahoo", symbol)
            failures = 0 if rec["status"] == "FETCHED" else failures + 1
            if not rec.get("cache_hit"):
                time.sleep(spacing)
        manifest["records"].append(rec)
        write_json(out / "manifest.json", manifest)
        print(symbol + ": " + rec["status"], flush=True)
    manifest["ecb"] = fetch("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml", out / "raw" / "ecb.xml", "ecb")
    manifest["finished_at"] = stamp()
    manifest["fetched_symbols"] = sum(r["status"] == "FETCHED" for r in manifest["records"])
    manifest["complete_acquisition"] = manifest["fetched_symbols"] == len(symbols) and manifest["ecb"]["status"] == "FETCHED"
    write_json(out / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--start", default="2024-10-01")
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", type=Path, default=Path("research-data"))
    args = parser.parse_args()
    symbols = json.loads(args.symbols.read_text(encoding="utf-8"))
    result = collect(symbols, args.start, args.end, args.output)
    print(json.dumps({"fetched": result["fetched_symbols"], "requested": len(result["symbols"]), "complete_acquisition": result["complete_acquisition"]}))
    return 0 if result["complete_acquisition"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

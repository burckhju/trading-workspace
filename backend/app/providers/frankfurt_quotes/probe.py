"""Read-only CSV coverage probe. ISINs must be supplied, never guessed from WKNs."""

import argparse
import asyncio
import csv
from collections import Counter
from pathlib import Path

from app.core.config.settings import get_settings
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient, utc_now
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError, assess_snapshot


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--input", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--delimiter", default=";")
    result.add_argument("--isin-column", default="ISIN")
    result.add_argument("--wkn-column", default="WKN")
    result.add_argument("--currency", default="EUR")
    return result


async def run(args: argparse.Namespace, client: FrankfurtSnapshotClient) -> dict[str, int]:
    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=args.delimiter))
    snapshot = None
    retrieved_at = utc_now()
    failure = None
    try:
        snapshot, retrieved_at, _hit = await client.load()
    except FrankfurtSourceError as exc:
        failure = str(exc)
    counts: Counter[str] = Counter()
    # Never overwrite the supplied table or an existing report.
    with args.output.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "row",
                "wkn",
                "isin",
                "status",
                "reason",
                "bid",
                "ask",
                "observed_at",
                "age_seconds",
                "source",
                "mic",
                "execution_usable",
            ],
            delimiter=args.delimiter,
        )
        writer.writeheader()
        for number, row in enumerate(rows, 1):
            isin = (row.get(args.isin_column) or "").strip().upper()
            wkn = (row.get(args.wkn_column) or "").strip().upper()
            output: dict[str, str | int | float | None] = {
                "row": number,
                "wkn": wkn,
                "isin": isin,
                "execution_usable": "false",
                "source": client.settings.source_name,
                "mic": "XFRA",
            }
            if not isin:
                output.update(status="UNAVAILABLE", reason="ISIN_REQUIRED_NO_WKN_GUESSING")
            elif snapshot is None:
                output.update(status="UNAVAILABLE", reason=failure)
            else:
                try:
                    item = assess_snapshot(
                        snapshot,
                        isin=isin,
                        wkn=wkn or None,
                        currency=args.currency,
                        now=utc_now(),
                        retrieved_at=retrieved_at,
                        max_age_seconds=client.settings.max_quote_age_seconds,
                    )
                    output.update(
                        status=item.status,
                        reason=item.reason,
                        age_seconds=item.age_seconds,
                        observed_at=item.observed_at.isoformat() if item.observed_at else None,
                        bid=str(item.record.bid) if item.record and item.record.bid else None,
                        ask=str(item.record.ask) if item.record and item.record.ask else None,
                    )
                except FrankfurtSourceError as exc:
                    output.update(status="ERROR", reason=str(exc))
            counts[str(output["status"])] += 1
            writer.writerow(output)
    return dict(counts)


def main() -> None:
    args = parser().parse_args()
    try:
        counts = asyncio.run(run(args, FrankfurtSnapshotClient(get_settings().market_data.frankfurt)))
    except (OSError, ValueError, csv.Error):
        raise SystemExit(
            "Frankfurt probe failed: check input/output paths and CSV configuration"
        ) from None
    print(counts)


if __name__ == "__main__":
    main()

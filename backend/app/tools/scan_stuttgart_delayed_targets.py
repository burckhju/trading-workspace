"""Read-only discovery scan for open positions in one official XSTU payload.

The command deliberately does not create listings, mappings, observations, or source
selections.  Its output is evidence for a later, separately reviewed preview/apply step.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.config.settings import StuttgartDelayedSettings
from app.core.di import ApplicationContainer
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
)
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
_PROVIDER = MarketDataProvider.BOERSE_STUTTGART_DELAYED
_XSTU_FILE_NAME = re.compile(r"^XSTU-pretrade-(?P<stamp>\d{8}T\d{4})\.json\.gz$")
_ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
_VERIFIED_SCHEMA = {
    "schema_version": "xstu-pretrade-flat-2026-09-04",
    "records_path": "$",
    "isin_field": "Isin",
    "mic_field": "VenueOfPublication",
    "bid_field": "Bid",
    "ask_field": "Ask",
    "currency_field": "PriceCurrency",
    "observed_at_field": "TransactionTime",
}


@dataclass(frozen=True, slots=True)
class OpenTarget:
    position_id: UUID
    warrant_id: UUID
    selection_id: UUID
    isin: str
    selection_status: str
    selection_reason: str


@dataclass(frozen=True, slots=True)
class TargetQuoteEvidence:
    isin: str
    bid: Decimal | None
    ask: Decimal | None
    currency: str
    observed_at: datetime


def _require_verified_schema(settings: StuttgartDelayedSettings) -> None:
    actual = {name: getattr(settings, name) for name in _VERIFIED_SCHEMA}
    if actual != _VERIFIED_SCHEMA:
        raise ValueError("STUTTGART_VERIFIED_SCHEMA_REQUIRED")


def _load_official_payload(path: Path) -> tuple[Any, str]:
    if not path.is_file():
        raise ValueError("STUTTGART_SOURCE_FILE_NOT_FOUND")
    if _XSTU_FILE_NAME.fullmatch(path.name) is None:
        raise ValueError("STUTTGART_SOURCE_FILE_NAME_INVALID")

    try:
        compressed = path.read_bytes()
        payload = json.loads(gzip.decompress(compressed).decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("STUTTGART_SOURCE_FILE_INVALID") from exc
    return payload, hashlib.sha256(compressed).hexdigest()


def _text(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _quote_side(record: dict[str, Any], field: str, *, isin: str) -> Decimal | None:
    value = record.get(field)
    if value is None:
        return None
    try:
        price = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"STUTTGART_TARGET_PRICE_INVALID_{isin}") from exc
    if not price.is_finite() or price < 0:
        raise ValueError(f"STUTTGART_TARGET_PRICE_INVALID_{isin}")
    return price if price > 0 else None


def _observed_at(value: str, *, isin: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"STUTTGART_TARGET_TIMESTAMP_INVALID_{isin}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"STUTTGART_TARGET_TIMESTAMP_INVALID_{isin}")
    return parsed.astimezone(UTC)


def scan_target_quotes(
    payload: Any,
    *,
    target_isins: set[str],
    settings: StuttgartDelayedSettings,
) -> tuple[dict[str, TargetQuoteEvidence], dict[str, int]]:
    """Select the latest exact XSTU/EUR quote for each requested ISIN."""

    _require_verified_schema(settings)
    normalized_targets = {isin.strip().upper() for isin in target_isins}
    invalid_isins = sorted(isin for isin in normalized_targets if _ISIN.fullmatch(isin) is None)
    if invalid_isins:
        raise ValueError("STUTTGART_TARGET_ISIN_INVALID_" + "_".join(invalid_isins))
    if not isinstance(payload, list):
        raise ValueError("STUTTGART_SOURCE_RECORDS_NOT_ARRAY")

    selected: dict[str, TargetQuoteEvidence] = {}
    rejected_rows: dict[str, int] = {}
    for record in payload:
        if not isinstance(record, dict):
            continue
        isin = _text(record, _VERIFIED_SCHEMA["isin_field"])
        if isin is None:
            continue
        isin = isin.upper()
        if isin not in normalized_targets:
            continue

        mic = _text(record, _VERIFIED_SCHEMA["mic_field"])
        if mic is None or mic.upper() != "XSTU":
            continue
        currency = _text(record, _VERIFIED_SCHEMA["currency_field"])
        timestamp = _text(record, _VERIFIED_SCHEMA["observed_at_field"])
        if currency is None or currency.upper() != "EUR" or timestamp is None:
            rejected_rows[isin] = rejected_rows.get(isin, 0) + 1
            continue

        bid = _quote_side(record, _VERIFIED_SCHEMA["bid_field"], isin=isin)
        ask = _quote_side(record, _VERIFIED_SCHEMA["ask_field"], isin=isin)
        if bid is None and ask is None:
            rejected_rows[isin] = rejected_rows.get(isin, 0) + 1
            continue
        observed_at = _observed_at(timestamp, isin=isin)
        candidate = TargetQuoteEvidence(
            isin=isin,
            bid=bid,
            ask=ask,
            currency="EUR",
            observed_at=observed_at,
        )

        previous = selected.get(isin)
        if previous is None or candidate.observed_at > previous.observed_at:
            selected[isin] = candidate
            continue
        if candidate.observed_at == previous.observed_at:
            selected[isin] = TargetQuoteEvidence(
                isin=isin,
                bid=(
                    max(previous.bid, candidate.bid)
                    if previous.bid is not None and candidate.bid is not None
                    else previous.bid or candidate.bid
                ),
                ask=(
                    min(previous.ask, candidate.ask)
                    if previous.ask is not None and candidate.ask is not None
                    else previous.ask or candidate.ask
                ),
                currency="EUR",
                observed_at=candidate.observed_at,
            )

    for isin, quote in selected.items():
        if quote.bid is not None and quote.ask is not None and quote.ask < quote.bid:
            raise ValueError(f"STUTTGART_TARGET_QUOTE_CROSSED_{isin}")
    return selected, dict(sorted(rejected_rows.items()))


async def _open_unselected_targets(
    container: ApplicationContainer,
) -> tuple[list[OpenTarget], int]:
    async with container.database.session_context() as session:
        rows = (
            await session.execute(
                select(
                    PositionModel.id.label("position_id"),
                    PositionModel.product_id.label("warrant_id"),
                    WarrantModel.isin,
                    PositionQuoteSourceSelectionModel.id.label("selection_id"),
                    PositionQuoteSourceSelectionModel.selection_status,
                    PositionQuoteSourceSelectionModel.selection_reason,
                )
                .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
                .join(
                    PositionQuoteSourceSelectionModel,
                    PositionQuoteSourceSelectionModel.position_id == PositionModel.id,
                )
                .where(
                    TradeModel.workspace_id == WORKSPACE_ID,
                    TradeModel.cancelled_at.is_(None),
                    PositionModel.open_quantity > 0,
                    PositionModel.closed_at.is_(None),
                    PositionQuoteSourceSelectionModel.superseded_at.is_(None),
                    PositionQuoteSourceSelectionModel.selection_status
                    == "NO_VERIFIED_QUOTE_SOURCE",
                )
                .order_by(WarrantModel.isin, PositionModel.id)
            )
        ).all()

    targets: list[OpenTarget] = []
    missing_isin = 0
    for row in rows:
        if row.isin is None:
            missing_isin += 1
            continue
        targets.append(
            OpenTarget(
                position_id=row.position_id,
                warrant_id=row.warrant_id,
                selection_id=row.selection_id,
                isin=str(row.isin).upper(),
                selection_status=str(row.selection_status),
                selection_reason=str(row.selection_reason),
            )
        )
    return targets, missing_isin


def _render_result(
    *,
    source_file: str,
    source_sha256: str,
    targets: list[OpenTarget],
    missing_isin_positions: int,
    quotes: dict[str, TargetQuoteEvidence],
    rejected_rows: dict[str, int],
    schema_version: str,
) -> dict[str, object]:
    by_isin: dict[str, list[OpenTarget]] = {}
    for target in targets:
        by_isin.setdefault(target.isin, []).append(target)

    matched: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    for isin, isin_targets in sorted(by_isin.items()):
        identity: dict[str, object] = {
            "isin": isin,
            "position_ids": [str(target.position_id) for target in isin_targets],
            "warrant_ids": sorted({str(target.warrant_id) for target in isin_targets}),
            "selection_ids": [str(target.selection_id) for target in isin_targets],
            "selection_statuses": sorted({target.selection_status for target in isin_targets}),
            "selection_reasons": sorted({target.selection_reason for target in isin_targets}),
        }
        quote = quotes.get(isin)
        if quote is None:
            missing.append(identity)
            continue
        matched.append(
            {
                **identity,
                "bid": str(quote.bid) if quote.bid is not None else None,
                "ask": str(quote.ask) if quote.ask is not None else None,
                "currency": quote.currency,
                "observed_at": quote.observed_at.isoformat(),
            }
        )

    return {
        "read_only": True,
        "workspace_id": str(WORKSPACE_ID),
        "provider": _PROVIDER.value,
        "mic": "XSTU",
        "schema_version": schema_version,
        "source_file": source_file,
        "source_sha256": source_sha256,
        "evidence_as_of": datetime.now(UTC).isoformat(),
        "open_unselected_count": len(targets) + missing_isin_positions,
        "target_isin_count": len(by_isin),
        "missing_isin_positions": missing_isin_positions,
        "matched_count": len(matched),
        "matched": matched,
        "missing_count": len(missing),
        "missing": missing,
        "rejected_target_rows": rejected_rows,
    }


async def run(*, payload_path: Path) -> dict[str, object]:
    settings = get_settings()
    stuttgart = settings.market_data.stuttgart_delayed
    _require_verified_schema(stuttgart)
    payload, source_sha256 = _load_official_payload(payload_path)

    container = ApplicationContainer.build(settings)
    try:
        targets, missing_isin_positions = await _open_unselected_targets(container)
    finally:
        await container.close()

    quotes, rejected_rows = scan_target_quotes(
        payload,
        target_isins={target.isin for target in targets},
        settings=stuttgart,
    )
    assert stuttgart.schema_version is not None
    return _render_result(
        source_file=payload_path.name,
        source_sha256=source_sha256,
        targets=targets,
        missing_isin_positions=missing_isin_positions,
        quotes=quotes,
        rejected_rows=rejected_rows,
        schema_version=stuttgart.schema_version,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "payload",
        type=Path,
        help="Path to one manually downloaded official XSTU-pretrade-YYYYMMDDTHHMM.json.gz",
    )
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(payload_path=args.payload)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

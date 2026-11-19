"""An indicative recovery must be comparable to the active loss observations."""

from datetime import UTC, datetime
from typing import Any

from app.features.position_monitoring.domain.indicative_entry import IndicativeDecision

PRICE_RANK = {"INDICATIVE_ISSUER": 1, "DELAYED_SOURCE_BID": 2, "SOURCE_BID": 3}
SCALE_RANK = {"CURRENT_UNIT_HISTORY_ASSUMED": 1, "DOCUMENTED": 2}


def product_scale_quality(material: dict[str, Any]) -> str:
    scale = material.get("product_scale") or {}
    quality = scale.get("quality")
    if quality in SCALE_RANK:
        return str(quality)
    return "DOCUMENTED" if scale.get("comparison_covered") is True else "UNAVAILABLE"


def _time(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    if result.utcoffset() is None:
        raise ValueError("Recovery evidence requires an aware ordering clock")
    return result.astimezone(UTC)


def _stream(material: dict[str, Any]) -> str:
    saved = material.get("saved_quote") or {}
    route = saved.get("route") or {}
    return f"{saved.get('provider')}:{route.get('identity_key')}"


def extend_loss_floor(
    floor: dict[str, Any] | None,
    *,
    material: dict[str, Any],
    result: dict[str, Any],
    opening_assessment_id: str,
) -> dict[str, Any]:
    """Join all accepted loss evidence, retaining each independent strong grade.

    An unknown-time receipt remains an explicit ordering boundary, never an
    invented original timestamp. It cannot be compared across unknown streams.
    """
    previous = floor or {}
    mode = result.get("evaluation_mode")
    rank = PRICE_RANK.get(mode or "", 0)
    ordering = _time(result.get("ordering_at"))
    old_ordering = _time(previous.get("ordering_bound_at"))
    bound = max((item for item in (ordering, old_ordering) if item is not None), default=None)
    streams = set(previous.get("unknown_streams", ()))
    if mode == "INDICATIVE_ISSUER":
        streams.add(_stream(material))
    currencies = set(previous.get("currencies", ()))
    currency = material.get("economic_basis", {}).get("cost_basis_currency")
    if currency:
        currencies.add(currency)
    isins = set(previous.get("isins", ()))
    if material.get("warrant_isin"):
        isins.add(material["warrant_isin"])
    return {
        "opening_assessment_id": opening_assessment_id,
        "price_rank": max(previous.get("price_rank", 0), rank),
        "scale_rank": max(
            previous.get("scale_rank", 0),
            SCALE_RANK.get(product_scale_quality(material), 0),
        ),
        "ordering_bound_at": bound.isoformat() if bound else None,
        "unknown_streams": sorted(streams),
        "currencies": sorted(currencies),
        "isins": sorted(isins),
    }


def recovery_problems(
    decision: IndicativeDecision,
    material: dict[str, Any],
    floor: dict[str, Any] | None,
) -> tuple[str, ...]:
    if floor is None or decision.outcome != "AT_OR_ABOVE_ENTRY":
        return ()
    rank = PRICE_RANK.get(decision.evaluation_mode or "", 0)
    scale_rank = SCALE_RANK.get(product_scale_quality(material), 0)
    problems: list[str] = []
    if rank < floor["price_rank"] or scale_rank < floor["scale_rank"]:
        problems.append("REVIEW_RECOVERY_EVIDENCE_WEAKER")
    currency = material.get("economic_basis", {}).get("cost_basis_currency")
    if (
        set(floor.get("currencies", ())) != {currency}
        or set(floor.get("isins", ())) != {material.get("warrant_isin")}
        or (
            decision.evaluation_mode == "INDICATIVE_ISSUER"
            and set(floor.get("unknown_streams", ())) != {_stream(material)}
        )
    ):
        problems.append("REVIEW_RECOVERY_SOURCE_NOT_COMPARABLE")
    bound = _time(floor.get("ordering_bound_at"))
    current = _time(decision.ordering_at)
    if bound is None or current is None:
        problems.append("REVIEW_RECOVERY_SOURCE_NOT_COMPARABLE")
    elif current < bound:
        problems.append("REVIEW_OUT_OF_ORDER_OBSERVATION")
    return tuple(dict.fromkeys(problems))

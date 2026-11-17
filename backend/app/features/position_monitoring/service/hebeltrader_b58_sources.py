"""Code-reviewed source paths, separate from payload shape and provider consent.

The production registry is intentionally empty: the inspected real suppliers do
not establish B58. No configuration flag, user declaration or JSON field can
add a path. A future supplier change must supply original-data/document evidence
and an implementation of its actual time semantics in a reviewed change.
"""

import re
from dataclasses import dataclass
from typing import Literal

from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.domain.status_observations import StatusEvidenceRead


@dataclass(frozen=True, slots=True)
class B58SourcePath:
    provider: str
    isin: str
    venue_mic: str
    source_contract: str
    source_reference: str
    qualification_reference: str
    qualification_sha256: str
    bid_time_field: str
    status_field: str
    status_time_field: str
    status_semantics: Literal["OBSERVED_AT_INSTANT"] = "OBSERVED_AT_INSTANT"

    def __post_init__(self) -> None:
        if any(not getattr(self, name).strip() for name in self.__dataclass_fields__):
            raise ValueError("A qualified source path requires complete original-field references")
        if not re.fullmatch(r"[0-9a-f]{64}", self.qualification_sha256):
            raise ValueError("A qualified source path requires its evidence digest")


@dataclass(frozen=True, slots=True)
class B58SourceAssessment:
    status: Literal["QUALIFIED", "NOT_QUALIFIED"]
    reasons: tuple[str, ...]
    qualification_reference: str | None = None
    qualification_sha256: str | None = None


QUALIFIED_B58_PATHS: tuple[B58SourcePath, ...] = ()


class B58SourceRegistry:
    """Explicit dependency seam for synthetic tests; no runtime activation API."""

    def __init__(self, paths: tuple[B58SourcePath, ...] = QUALIFIED_B58_PATHS) -> None:
        self._paths = paths

    @property
    def qualification_references(self) -> tuple[str, ...]:
        return tuple(path.qualification_reference for path in self._paths)

    def qualify(
        self,
        saved: SavedQuoteEvidence,
        status: StatusEvidenceRead | None,
    ) -> B58SourceAssessment:
        quote = saved.quote
        evidence = quote.original_evidence if quote else None
        route = saved.route
        if evidence is None or route is None:
            return B58SourceAssessment("NOT_QUALIFIED", ("B58_ORIGINAL_SUPPLY_MISSING",))
        paths = [
            path
            for path in self._paths
            if (
                path.provider == saved.provider
                and path.isin == evidence.isin
                and path.venue_mic == evidence.venue_mic == route.venue_mic
                and path.source_contract == evidence.source_contract
                and path.source_reference == evidence.source_reference
                and evidence.bid is not None
                and path.bid_time_field == evidence.bid.source_field
            )
        ]
        if len(paths) != 1:
            return B58SourceAssessment("NOT_QUALIFIED", ("B58_REAL_SOURCE_PATH_NOT_QUALIFIED",))
        path = paths[0]
        if (
            status is None
            or status.point_verdict != "OBSERVED_AT_INSTANT"
            or status.observed_status != "OPEN"
            or not status.point_observations
            or status.route.workspace_id != route.workspace_id
            or status.route.warrant_listing_id != route.warrant_listing_id
            or status.route.warrant_id != route.warrant_id
            or status.route.identity_key != route.identity_key
            or status.route.provider != saved.provider
            or status.route.isin != evidence.isin
            or status.route.venue_mic != route.venue_mic
        ):
            return B58SourceAssessment("NOT_QUALIFIED", ("B58_OPEN_AT_EVALUATION_NOT_PROVEN",))
        for observation in status.point_observations:
            original = observation.original
            if (
                original is None
                or original.source_contract != path.source_contract
                or original.source_reference != path.source_reference
                or original.source_status_field != path.status_field
                or original.source_time_field != path.status_time_field
                or original.temporal_meaning != path.status_semantics
            ):
                return B58SourceAssessment("NOT_QUALIFIED", ("B58_STATUS_SOURCE_MISMATCH",))
        latest = status.latest_capture.original if status.latest_capture else None
        if latest is not None and (
            latest.source_contract != path.source_contract
            or latest.source_reference != path.source_reference
        ):
            return B58SourceAssessment("NOT_QUALIFIED", ("B58_STATUS_SOURCE_CHANGED",))
        if status.latest_gap is not None and status.latest_gap.captured_at >= max(
            item.captured_at for item in status.point_observations
        ):
            return B58SourceAssessment("NOT_QUALIFIED", ("B58_SUPPLY_GAP_AT_EVALUATION",))
        return B58SourceAssessment(
            "QUALIFIED",
            (),
            path.qualification_reference,
            path.qualification_sha256,
        )

"""Centrally selected policies for one durable indicative review family."""

from dataclasses import dataclass
from typing import Literal

type ReviewActivationScope = Literal["DISABLED", "INDICATIVE_ENTRY_V1", "INDICATIVE_ENTRY_V2"]


@dataclass(frozen=True, slots=True)
class IndicativeReviewPolicy:
    scope: Literal["INDICATIVE_ENTRY_V1", "INDICATIVE_ENTRY_V2"]
    version: str
    delayed_bid_max_age_seconds: int | None = None
    allow_assumed_product_history: bool = False

    @property
    def key(self) -> str:
        return f"{self.scope}:{self.version}"


V1_POLICY = IndicativeReviewPolicy("INDICATIVE_ENTRY_V1", "indicative-entry-review-v1")
V2_POLICY = IndicativeReviewPolicy("INDICATIVE_ENTRY_V2", "indicative-entry-review-v2", 1800, True)
REVIEW_FAMILY_VERSIONS = (V1_POLICY.version, V2_POLICY.version)


def review_policy(scope: str) -> IndicativeReviewPolicy:
    if scope == V2_POLICY.scope:
        return V2_POLICY
    if scope in {"DISABLED", V1_POLICY.scope}:
        return V1_POLICY
    raise ValueError("Unknown indicative review activation scope")

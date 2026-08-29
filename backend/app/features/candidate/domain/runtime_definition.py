"""Fail-closed adapter from governed model definitions to Candidate executable rules."""

from __future__ import annotations

from dataclasses import dataclass

from app.features.analysis.domain.top_down import ContextClassification, TradingDirection

SUPPORTED_SCHEMA = "TOP_DOWN_CANDIDATE/1.0"
_SUPPORTED_KEYS = {"schema", "direction", "market_context_allowed"}


@dataclass(frozen=True, slots=True)
class CandidateRuntimeRules:
    """Executable Candidate rules resolved from one governed model version."""

    model_id: str
    model_version: str
    direction: TradingDirection
    market_context_allowed: frozenset[ContextClassification]


def adapt_candidate_runtime_definition(
    *,
    model_key: str,
    version: int,
    definition: dict[str, object],
) -> CandidateRuntimeRules:
    """Translate only the explicitly supported Candidate 1.0 governed schema.

    Unknown keys are rejected deliberately so governance definitions cannot appear
    active while executable code silently ignores unsupported semantics.
    """

    if model_key != "TOP_DOWN_CANDIDATE":
        raise ValueError("unsupported governed model key for Candidate evaluation")
    if version <= 0:
        raise ValueError("governed model version must be positive")

    unknown = set(definition) - _SUPPORTED_KEYS
    if unknown:
        raise ValueError(f"unsupported Candidate definition keys: {', '.join(sorted(unknown))}")
    if definition.get("schema") != SUPPORTED_SCHEMA:
        raise ValueError("unsupported Candidate definition schema")
    if definition.get("direction") != TradingDirection.LONG.value:
        raise ValueError("TOP_DOWN_CANDIDATE/1.0 supports LONG evaluations only")

    raw_contexts = definition.get("market_context_allowed")
    if not isinstance(raw_contexts, list) or not raw_contexts:
        raise ValueError("market_context_allowed must be a non-empty list")
    try:
        contexts = frozenset(ContextClassification(str(item)) for item in raw_contexts)
    except ValueError as exc:
        raise ValueError("market_context_allowed contains an unsupported context") from exc

    supported_contexts = {
        ContextClassification.FAVORABLE,
        ContextClassification.CAUTIOUS,
    }
    if not contexts <= supported_contexts:
        raise ValueError("TOP_DOWN_CANDIDATE/1.0 supports FAVORABLE and CAUTIOUS contexts only")

    return CandidateRuntimeRules(
        model_id=model_key,
        model_version=str(version),
        direction=TradingDirection.LONG,
        market_context_allowed=contexts,
    )

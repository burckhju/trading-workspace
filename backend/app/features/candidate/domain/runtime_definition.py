"""Fail-closed adapter from governed model definitions to Candidate executable rules."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.features.analysis.domain.top_down import ContextClassification, TradingDirection
from app.features.candidate.domain.models import CandidateEvaluationInput, CandidateEvaluationResult
from app.features.candidate.domain.qualification import evaluate_candidate

SUPPORTED_SCHEMA = "TOP_DOWN_CANDIDATE/1.0"
_SUPPORTED_KEYS = {"schema", "direction", "market_context_allowed"}
_SUPPORTED_CONTEXTS = frozenset(
    {
        ContextClassification.FAVORABLE,
        ContextClassification.CAUTIOUS,
    }
)


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

    V1 intentionally accepts only semantics identical to the existing executable
    engine. Unknown or changed semantics fail closed until a separately implemented
    and governed executable schema exists.
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
    if contexts != _SUPPORTED_CONTEXTS:
        raise ValueError("TOP_DOWN_CANDIDATE/1.0 requires FAVORABLE and CAUTIOUS contexts")

    return CandidateRuntimeRules(
        model_id=model_key,
        model_version=str(version),
        direction=TradingDirection.LONG,
        market_context_allowed=contexts,
    )


def evaluate_candidate_with_runtime_rules(
    value: CandidateEvaluationInput,
    rules: CandidateRuntimeRules,
) -> CandidateEvaluationResult:
    """Execute the supported governed rules and attach truthful governed provenance."""

    compatible = (
        rules.direction is TradingDirection.LONG
        and rules.market_context_allowed == _SUPPORTED_CONTEXTS
    )
    if not compatible:
        raise ValueError("Candidate runtime rules are incompatible with executable schema 1.0")
    result = evaluate_candidate(value)
    return replace(result, model_id=rules.model_id, model_version=rules.model_version)

"""Fail-closed adapter from governed model definitions to Candidate executable rules."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.features.analysis.domain.top_down import ContextClassification, TradingDirection
from app.features.candidate.domain.models import CandidateEvaluationInput, CandidateEvaluationResult
from app.features.candidate.domain.qualification import (
    evaluate_candidate,
    evaluate_candidate_with_market_context_rule,
)

SUPPORTED_SCHEMA = "TOP_DOWN_CANDIDATE/1.0"
SUPPORTED_SCHEMA_V2 = "TOP_DOWN_CANDIDATE/2.0"
_SUPPORTED_KEYS = {"schema", "direction", "market_context_allowed"}
_LEGACY_CONTEXTS = frozenset(
    {
        ContextClassification.FAVORABLE,
        ContextClassification.CAUTIOUS,
    }
)
_STRICT_CONTEXTS = frozenset({ContextClassification.FAVORABLE})
_SUPPORTED_V2_CONTEXT_CONFIGURATIONS = frozenset({_STRICT_CONTEXTS, _LEGACY_CONTEXTS})


@dataclass(frozen=True, slots=True)
class CandidateRuntimeRules:
    """Executable Candidate rules resolved from one governed model version."""

    model_id: str
    model_version: str
    direction: TradingDirection
    market_context_allowed: frozenset[ContextClassification]
    schema: str = SUPPORTED_SCHEMA


def adapt_candidate_runtime_definition(
    *,
    model_key: str,
    version: int,
    definition: dict[str, object],
) -> CandidateRuntimeRules:
    """Translate only explicitly implemented Candidate governed schemas."""

    if model_key != "TOP_DOWN_CANDIDATE":
        raise ValueError("unsupported governed model key for Candidate evaluation")
    if version <= 0:
        raise ValueError("governed model version must be positive")

    unknown = set(definition) - _SUPPORTED_KEYS
    if unknown:
        raise ValueError(f"unsupported Candidate definition keys: {', '.join(sorted(unknown))}")

    schema = definition.get("schema")
    if schema not in {SUPPORTED_SCHEMA, SUPPORTED_SCHEMA_V2}:
        raise ValueError("unsupported Candidate definition schema")
    if definition.get("direction") != TradingDirection.LONG.value:
        raise ValueError(f"{schema} supports LONG evaluations only")

    raw_contexts = definition.get("market_context_allowed")
    if not isinstance(raw_contexts, list) or not raw_contexts:
        raise ValueError("market_context_allowed must be a non-empty list")
    try:
        contexts = frozenset(ContextClassification(str(item)) for item in raw_contexts)
    except ValueError as exc:
        raise ValueError("market_context_allowed contains an unsupported context") from exc

    if schema == SUPPORTED_SCHEMA:
        if contexts != _LEGACY_CONTEXTS:
            raise ValueError("TOP_DOWN_CANDIDATE/1.0 requires FAVORABLE and CAUTIOUS contexts")
    elif contexts not in _SUPPORTED_V2_CONTEXT_CONFIGURATIONS:
        raise ValueError(
            "TOP_DOWN_CANDIDATE/2.0 allows FAVORABLE alone or FAVORABLE and CAUTIOUS"
        )

    return CandidateRuntimeRules(
        model_id=model_key,
        model_version=str(version),
        direction=TradingDirection.LONG,
        market_context_allowed=contexts,
        schema=str(schema),
    )


def evaluate_candidate_with_runtime_rules(
    value: CandidateEvaluationInput,
    rules: CandidateRuntimeRules,
) -> CandidateEvaluationResult:
    """Execute the supported governed rules and attach truthful governed provenance."""

    if rules.direction is not TradingDirection.LONG:
        raise ValueError("Candidate runtime rules require LONG direction")

    if rules.schema == SUPPORTED_SCHEMA:
        if rules.market_context_allowed != _LEGACY_CONTEXTS:
            raise ValueError("Candidate runtime rules are incompatible with executable schema 1.0")
        result = evaluate_candidate(value)
    elif rules.schema == SUPPORTED_SCHEMA_V2:
        if rules.market_context_allowed not in _SUPPORTED_V2_CONTEXT_CONFIGURATIONS:
            raise ValueError("Candidate runtime rules are incompatible with executable schema 2.0")
        result = evaluate_candidate_with_market_context_rule(
            value,
            market_context_allowed=rules.market_context_allowed,
        )
    else:
        raise ValueError("Candidate runtime rules use an unsupported executable schema")

    return replace(result, model_id=rules.model_id, model_version=rules.model_version)

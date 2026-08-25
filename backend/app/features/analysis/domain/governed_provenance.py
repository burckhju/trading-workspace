"""Governed provenance contract for the released FT-006 runtime model.

This module describes the code artifact that the legacy runtime identity
EOD_TREND_MOMENTUM/1.0.0 represents.  It does not load rules dynamically and
it does not select or activate a newer governed version.
"""

from __future__ import annotations

from typing import Final

from app.features.analysis.domain.calculator import MODEL_ID, MODEL_VERSION

RUNTIME_CONTRACT: Final = "FT-006:EOD_TREND_MOMENTUM:1.0.0"
IMPLEMENTATION_REF: Final = "backend/app/features/analysis/domain/calculator.py@8dcead013709d1ba2ad40e180fcc65ebe1c6589e"
RULE_REPRESENTATION: Final = "CODE_PLUS_PARAMETERS"


def governed_baseline_definition() -> dict[str, object]:
    """Return the exact metadata required for the released legacy baseline."""
    return {
        "runtime_contract": RUNTIME_CONTRACT,
        "runtime_model_id": MODEL_ID,
        "runtime_model_version": MODEL_VERSION,
        "implementation_ref": IMPLEMENTATION_REF,
        "rule_representation": RULE_REPRESENTATION,
    }


def matches_governed_baseline(definition: dict[str, object]) -> bool:
    """Return whether a governed definition represents the released runtime."""
    expected = governed_baseline_definition()
    return all(definition.get(key) == value for key, value in expected.items())

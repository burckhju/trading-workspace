from types import SimpleNamespace

import pytest

from app.features.market_data.domain.enums import MappingStatus
from app.tools.refresh_bound_gettex_quotes import _digest, _validate_binding


def _binding(**changes):
    values = {
        "provider": "GETTEX_DELAYED",
        "mic": "MUND",
        "provider_exchange_code": "MUND",
        "mapping_status": MappingStatus.ACTIVE,
        "persisted_mapping_version": 2,
        "current_mapping_version": 2,
        "identity_key": "a" * 64,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_bound_gettex_binding_requires_exact_mund_identity():
    _validate_binding(_binding())

    with pytest.raises(ValueError, match="ROUTE_NOT_MUND"):
        _validate_binding(_binding(mic="XFRA"))

    with pytest.raises(ValueError, match="MAPPING_VERSION_CHANGED"):
        _validate_binding(_binding(current_mapping_version=3))


def test_bound_gettex_preview_digest_is_stable_and_binding_sensitive():
    payload = {
        "workspace_id": "workspace",
        "provider": "GETTEX_DELAYED",
        "historical_as_of": "2026-09-18T19:45:00+00:00",
        "bindings": [{"listing_id": "listing", "mapping_version": 2}],
        "historical_evidence": {"DE000TEST001": "2026-09-18T19:44:00+00:00"},
    }

    first = _digest(payload)
    second = _digest(dict(payload))

    assert first == second
    assert len(first) == 64

    changed = {
        **payload,
        "bindings": [{"listing_id": "listing", "mapping_version": 3}],
    }
    assert _digest(changed) != first

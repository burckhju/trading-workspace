from types import SimpleNamespace

import pytest

from app.core.config.frankfurt import FrankfurtQuoteSettings, FrankfurtSourceMode
from app.tools.reselect_verified_frankfurt_positions import _digest, _require_runtime


def _container(**changes):
    values = {
        "enabled": True,
        "usage_approved": True,
        "contract_verified": True,
        "source_mode": FrankfurtSourceMode.PUBLIC_WEBSITE,
        "source_name": "deutsche-boerse-public",
    }
    values.update(changes)
    settings = FrankfurtQuoteSettings(**values)
    return SimpleNamespace(
        settings=SimpleNamespace(market_data=SimpleNamespace(frankfurt=settings))
    )


def test_reselection_runtime_requires_public_website_contract():
    _require_runtime(_container())

    with pytest.raises(ValueError, match="FRANKFURT_MUST_BE_ENABLED"):
        _require_runtime(_container(enabled=False))

    with pytest.raises(ValueError, match="USAGE_APPROVAL_REQUIRED"):
        _require_runtime(_container(usage_approved=False))

    with pytest.raises(ValueError, match="CONTRACT_VERIFICATION_REQUIRED"):
        _require_runtime(_container(contract_verified=False))

    with pytest.raises(ValueError, match="PUBLIC_WEBSITE_MODE_REQUIRED"):
        _require_runtime(
            _container(
                source_mode=FrankfurtSourceMode.HTTPS_JSON,
                source_name="vendor-feed",
                snapshot_url="https://example.com/feed",
                allowed_host="example.com",
            )
        )


def test_reselection_preview_digest_is_stable_and_evidence_sensitive():
    payload = {
        "workspace_id": "workspace",
        "provider": "FRANKFURT_QUOTES",
        "source_mode": "public_website",
        "source_name": "deutsche-boerse-public",
        "eligible": [
            {
                "position_id": "position",
                "mapping_version": 1,
                "identity_key": "a" * 64,
                "observation": {
                    "retrieved_at": "2026-09-19T14:02:22+00:00",
                    "reference_price": "0.078",
                    "reference_price_type": "LAST_TRADE",
                },
            }
        ],
        "excluded": {
            "no_verified_mapping": 17,
            "multiple_or_other_routes": 4,
        },
    }

    first = _digest(payload)
    assert first == _digest(dict(payload))
    assert len(first) == 64

    changed = {
        **payload,
        "eligible": [
            {
                "position_id": "position",
                "mapping_version": 1,
                "identity_key": "a" * 64,
                "observation": {
                    "retrieved_at": "2026-09-19T14:02:22+00:00",
                    "reference_price": "0.079",
                    "reference_price_type": "LAST_TRADE",
                },
            }
        ],
    }
    assert _digest(changed) != first

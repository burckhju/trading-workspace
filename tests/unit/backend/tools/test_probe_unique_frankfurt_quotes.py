from types import SimpleNamespace

import pytest

from app.core.config.frankfurt import FrankfurtQuoteSettings, FrankfurtSourceMode
from app.tools.probe_unique_frankfurt_quotes import _digest, _require_public_runtime


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


def test_public_runtime_requires_explicit_approval_and_verified_contract():
    _require_public_runtime(_container())

    with pytest.raises(ValueError, match="USAGE_APPROVAL_REQUIRED"):
        _require_public_runtime(_container(usage_approved=False))

    with pytest.raises(ValueError, match="CONTRACT_VERIFICATION_REQUIRED"):
        _require_public_runtime(_container(contract_verified=False))


def test_public_runtime_requires_public_website_identity():
    with pytest.raises(ValueError, match="PUBLIC_WEBSITE_MODE_REQUIRED"):
        _require_public_runtime(
            _container(
                source_mode=FrankfurtSourceMode.HTTPS_JSON,
                source_name="vendor-feed",
                snapshot_url="https://example.com/feed",
                allowed_host="example.com",
            )
        )

    with pytest.raises(ValueError, match="PUBLIC_SOURCE_NAME_REQUIRED"):
        _require_public_runtime(_container(source_name="wrong-source"))


def test_frankfurt_probe_preview_digest_is_stable_and_route_sensitive():
    payload = {
        "workspace_id": "workspace",
        "provider": "FRANKFURT_QUOTES",
        "source_mode": "public_website",
        "source_name": "deutsche-boerse-public",
        "eligible": [
            {
                "listing_id": "listing",
                "mapping_id": "mapping",
                "mapping_version": 1,
                "identity_key": "a" * 64,
            }
        ],
        "excluded": {
            "no_verified_mapping": 17,
            "multiple_verified_routes": 4,
            "other_unique_route": 0,
        },
    }

    first = _digest(payload)
    assert first == _digest(dict(payload))
    assert len(first) == 64

    changed = {
        **payload,
        "eligible": [
            {
                "listing_id": "listing",
                "mapping_id": "mapping",
                "mapping_version": 2,
                "identity_key": "a" * 64,
            }
        ],
    }
    assert _digest(changed) != first

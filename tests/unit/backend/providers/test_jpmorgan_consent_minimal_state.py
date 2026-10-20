"""Exercise real storage limits and preserve validation of the actual saved state."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.providers.issuer_renderer import consent_state
from app.tools import setup_jpmorgan_consent as setup

ISIN = "DE000JZ91459"
URL = "https://www.jpmorgan-zertifikate.de/zertifikate-detail/" + ISIN
DIGEST = "5b91cb6c6b389362df312b3f4fdf72fddb36e407a67f1c73b6d4433c011f3d1b"
SECRET = "server-generated-cookie-value-never-log"


def state(*, storage_size: int = 0, cookie_size: int = 0, cookies: bool = True):
    return {
        "cookies": (
            [
                {
                    "domain": ".jpmorgan-zertifikate.de",
                    "name": "test-consent",
                    "value": SECRET + "x" * cookie_size,
                }
            ]
            if cookies
            else []
        ),
        "origins": [
            {
                "origin": "https://www.jpmorgan-zertifikate.de",
                "localStorage": [{"name": "large-site-cache", "value": "x" * storage_size}],
            }
        ],
    }


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "state.json"
    monkeypatch.setattr(setup, "STATE_PATH", path)
    writes = []

    def save(value, digest):
        writes.append(value)
        consent_state.save_consent(value, digest, path)

    monkeypatch.setattr(setup, "save_consent", save)
    return SimpleNamespace(path=path, writes=writes)


@pytest.mark.asyncio
async def test_small_full_state_is_saved_with_existing_writer_after_reuse(storage):
    value = state()
    renderer = SimpleNamespace(_capture=AsyncMock())
    result = await setup.verify_and_save_consent(renderer, value, DIGEST, ISIN, URL)
    assert result["consent_storage_mode"] == "FULL_SCOPED_STATE_VERIFIED"
    renderer._capture.assert_awaited_once_with("JPMORGAN", ISIN, URL, consent_override=value)
    assert consent_state.load_consent(storage.path) == value
    assert storage.path.stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_oversized_state_uses_same_cookies_only_after_new_product_verification(storage):
    value = state(storage_size=300_000)
    minimal = {"cookies": value["cookies"], "origins": []}
    observed = []

    async def capture(provider, isin, url, *, consent_override):
        assert not storage.path.exists(), "No state may be saved before successful reuse"
        observed.append(consent_override)

    renderer = SimpleNamespace(_capture=AsyncMock(side_effect=capture))
    result = await setup.verify_and_save_consent(renderer, value, DIGEST, ISIN, URL)
    assert observed == [value, minimal]
    assert storage.writes == [value, minimal]
    assert consent_state.load_consent(storage.path) == minimal
    assert storage.path.stat().st_size < 262_144
    assert storage.path.stat().st_mode & 0o777 == 0o600
    assert result["consent_storage_mode"] == "SCOPED_COOKIES_ONLY_VERIFIED"
    assert result["consent_storage_diagnostics"]["cookie_only_product_reuse_verified"] is True
    assert SECRET not in json.dumps(result)
    assert "large-site-cache" not in json.dumps(result)


@pytest.mark.asyncio
async def test_failed_cookie_only_reuse_preserves_existing_saved_state(storage):
    existing = state()
    consent_state.save_consent(existing, DIGEST, storage.path)
    before = storage.path.read_bytes()
    renderer = SimpleNamespace(
        _capture=AsyncMock(side_effect=[None, ValueError("ISSUER_RENDER_TERMS_REQUIRED")])
    )
    with pytest.raises(setup.ConsentStateNotStored) as caught:
        await setup.verify_and_save_consent(
            renderer, state(storage_size=300_000), DIGEST, ISIN, URL
        )
    assert str(caught.value) == "ISSUER_CONSENT_COOKIE_ONLY_REUSE_FAILED"
    assert caught.value.diagnostics["cookie_only_reuse_reason"] == "ISSUER_RENDER_TERMS_REQUIRED"
    assert storage.path.read_bytes() == before
    assert len(storage.writes) == 1


@pytest.mark.asyncio
async def test_cookie_only_state_must_still_fit_unchanged_size_limit(storage):
    renderer = SimpleNamespace(_capture=AsyncMock())
    with pytest.raises(setup.ConsentStateNotStored) as caught:
        await setup.verify_and_save_consent(
            renderer, state(storage_size=300_000, cookie_size=300_000), DIGEST, ISIN, URL
        )
    assert str(caught.value) == "ISSUER_CONSENT_COOKIE_ONLY_NOT_STORED"
    assert renderer._capture.await_count == 2
    assert not storage.path.exists()


@pytest.mark.asyncio
async def test_missing_cookies_does_not_invent_a_smaller_consent(storage):
    renderer = SimpleNamespace(_capture=AsyncMock())
    with pytest.raises(setup.ConsentStateNotStored, match="NO_SMALLER_COOKIE_STATE"):
        await setup.verify_and_save_consent(
            renderer, state(storage_size=300_000, cookies=False), DIGEST, ISIN, URL
        )
    assert renderer._capture.await_count == 1
    assert not storage.path.exists()


@pytest.mark.asyncio
async def test_symlink_is_rejected_before_browser_and_its_target_untouched(storage, monkeypatch):
    target = storage.path.parent / "existing.json"
    target.write_text("existing data")
    storage.path.symlink_to(target)
    factory = Mock()
    monkeypatch.setattr(setup, "IssuerRenderer", factory)
    with pytest.raises(setup.ConsentStateNotStored, match="DESTINATION_SYMLINK"):
        await setup.setup(confirm=DIGEST, accepted=True, eligibility_confirmed=True)
    factory.assert_not_called()
    assert storage.path.is_symlink()
    assert target.read_text() == "existing data"


@pytest.mark.asyncio
async def test_first_product_reuse_failure_never_saves(storage):
    renderer = SimpleNamespace(_capture=AsyncMock(side_effect=ValueError("IDENTITY_MISMATCH")))
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        await setup.verify_and_save_consent(
            renderer, state(storage_size=300_000), DIGEST, ISIN, URL
        )
    assert storage.writes == []
    assert not storage.path.exists()


@pytest.mark.asyncio
async def test_io_failure_does_not_trigger_cookie_fallback(storage, monkeypatch):
    save = Mock(side_effect=PermissionError("private path"))
    monkeypatch.setattr(setup, "save_consent", save)
    renderer = SimpleNamespace(_capture=AsyncMock())
    with pytest.raises(PermissionError):
        await setup.verify_and_save_consent(
            renderer, state(storage_size=300_000), DIGEST, ISIN, URL
        )
    assert renderer._capture.await_count == 1
    save.assert_called_once()

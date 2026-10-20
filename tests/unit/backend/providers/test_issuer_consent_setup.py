"""Terms gate regression and explicit approval/state persistence boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.providers.issuer_pages import is_jpmorgan_terms_page, parse_product_page
from app.providers.issuer_renderer import browser as browser_module
from app.providers.issuer_renderer.consent_state import (
    load_consent,
    restrict_state,
    save_consent,
)
from app.tools.setup_jpmorgan_consent import (
    require_confirmation,
    same_origin,
    terms_digest,
)
from tests.unit.backend.features.market_data.test_issuer_route_discovery import page as product_page

TERMS = (
    "WICHTIGE HINWEISE UND NUTZUNGSBEDINGUNGEN "
    "Die Nutzung dieser Website ist nur Nutzern gestattet, welche "
    "die Zustimmung durch Anklicken des Bestätigungsbuttons erteilen."
)
ISIN = "DE000JZ91459"
URL = "https://www.jpmorgan-zertifikate.de/zertifikate-detail/" + ISIN


def test_full_page_terms_detected_without_a_dialog_or_heading() -> None:
    assert is_jpmorgan_terms_page(TERMS, has_product_bindings=False)
    assert not is_jpmorgan_terms_page(TERMS, has_product_bindings=True)
    assert not is_jpmorgan_terms_page(
        "Nutzungsbedingungen Cookie-Einstellungen", has_product_bindings=False
    )
    with pytest.raises(ValueError, match=r"^ISSUER_PAGE_TERMS_REQUIRED$"):
        parse_product_page(f"<body><div>{TERMS}</div></body>".encode(), "JPMORGAN", ISIN, URL)


@pytest.mark.parametrize("approved,changed", [(False, False), (True, True)])
def test_no_acceptance_without_current_reviewed_hash(approved: bool, changed: bool) -> None:
    _, digest = terms_digest(TERMS)
    with pytest.raises(ValueError, match="CONFIRMATION_MISSING_OR_CHANGED"):
        require_confirmation(digest, "f" * 64 if changed else digest, approved)


def test_terms_whitespace_is_stable_but_content_change_invalidates() -> None:
    assert terms_digest(TERMS)[1] == terms_digest(TERMS.replace(" ", " \n "))[1]
    assert terms_digest(TERMS)[1] != terms_digest(TERMS + " Neue Bedingung.")[1]


def test_consent_storage_scoped_to_jpmorgan_and_private(tmp_path: Path) -> None:
    # Cookies are protocol JSON. The values remain local and are never report fields.
    state = {
        "cookies": [
            {"domain": ".jpmorgan-zertifikate.de", "name": "consent", "value": "yes"},
            {"domain": "other.invalid", "name": "cookie", "value": "secret"},
        ],
        "origins": [
            {"origin": "https://www.jpmorgan-zertifikate.de", "localStorage": []},
            {"origin": "https://other.invalid", "localStorage": []},
        ],
    }
    path = tmp_path / "state.json"
    save_consent(state, "a" * 64, path)
    assert path.stat().st_mode & 0o777 == 0o600
    assert load_consent(path) == restrict_state(state)
    assert "other.invalid" not in path.read_text()
    record = json.loads(path.read_text())
    record["storage_state"]["cookies"].append({"domain": "other.invalid"})
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="CONSENT_STATE_INVALID"):
        load_consent(path)


def test_setup_cannot_approve_external_or_insecure_navigation() -> None:
    assert same_origin(URL)
    for value in (
        "http://www.jpmorgan-zertifikate.de",
        "https://www.jpmorgan-zertifikate.de.evil.test",
        "https://user:secret@www.jpmorgan-zertifikate.de",
        "https://www.jpmorgan-zertifikate.de:444",
    ):
        assert not same_origin(value)


@pytest.mark.asyncio
async def test_renderer_returns_terms_reason_immediately_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = SimpleNamespace(
        main_frame=object(),
        url=URL,
        goto=AsyncMock(
            return_value=SimpleNamespace(status=200, headers={"content-type": "text/html"})
        ),
    )
    page.evaluate = AsyncMock(side_effect=[None, f"<body>{TERMS}</body>"])
    context = SimpleNamespace(
        new_page=AsyncMock(return_value=page),
        route=AsyncMock(),
        route_web_socket=AsyncMock(),
        close=AsyncMock(),
    )
    renderer = browser_module.IssuerRenderer()
    renderer.browser = SimpleNamespace(
        new_context=AsyncMock(return_value=context), is_connected=lambda: True
    )
    monkeypatch.setattr(browser_module, "load_consent", lambda: None)
    with pytest.raises(browser_module.RenderFailure, match=r"^ISSUER_RENDER_TERMS_REQUIRED$"):
        await renderer.render("JPMORGAN", ISIN)
    assert page.evaluate.await_count == 2
    context.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_or_changed_confirmation_never_clicks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tools import setup_jpmorgan_consent as tool

    control = SimpleNamespace(count=AsyncMock(return_value=1), click=AsyncMock())
    control.or_ = lambda _: control
    page = SimpleNamespace(
        main_frame=object(),
        goto=AsyncMock(return_value=SimpleNamespace(status=200)),
        get_by_role=lambda *a, **kw: control,
        locator=lambda *a: control,
    )
    context = SimpleNamespace(
        new_page=AsyncMock(return_value=page),
        route=AsyncMock(),
        route_web_socket=AsyncMock(),
        close=AsyncMock(),
    )
    renderer = SimpleNamespace(
        start=AsyncMock(),
        close=AsyncMock(),
        browser=SimpleNamespace(new_context=AsyncMock(return_value=context)),
    )
    monkeypatch.setattr(tool, "IssuerRenderer", lambda: renderer)
    monkeypatch.setattr(tool, "inspect_terms", AsyncMock(return_value=terms_digest(TERMS)))
    monkeypatch.setattr(tool, "inspect_form", AsyncMock(return_value={"accept_control_count": 1}))
    choices = AsyncMock()
    monkeypatch.setattr(tool, "apply_choices", choices)
    preview = await tool.setup(confirm=None, accepted=False)
    assert preview["accepted"] is False and preview["status"] == "REVIEW_REQUIRED"
    control.click.assert_not_awaited()
    with pytest.raises(ValueError, match="CONFIRMATION_MISSING_OR_CHANGED"):
        await tool.setup(confirm="f" * 64, accepted=True, eligibility_confirmed=True)
    control.click.assert_not_awaited()
    choices.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("reuse_ok", [True, False])
@pytest.mark.parametrize("include_clock", [True, False])
async def test_state_saved_only_after_verified_fresh_context(
    monkeypatch: pytest.MonkeyPatch, reuse_ok: bool, include_clock: bool
) -> None:
    from app.tools import setup_jpmorgan_consent as tool

    control = SimpleNamespace(
        count=AsyncMock(return_value=1),
        click=AsyncMock(),
        evaluate=AsyncMock(return_value=None),
        wait_for=AsyncMock(),
    )
    control.or_ = lambda _: control
    page = SimpleNamespace(
        main_frame=object(),
        url=URL,
        goto=AsyncMock(return_value=SimpleNamespace(status=200)),
        get_by_role=lambda *a, **kw: control,
        locator=lambda *a: control,
        evaluate=AsyncMock(
            return_value=product_page(isin=ISIN, include_clock=include_clock).decode()
        ),
    )
    state = {
        "cookies": [],
        "origins": [{"origin": "https://www.jpmorgan-zertifikate.de", "localStorage": []}],
    }
    context = SimpleNamespace(
        new_page=AsyncMock(return_value=page),
        route=AsyncMock(),
        route_web_socket=AsyncMock(),
        close=AsyncMock(),
        storage_state=AsyncMock(return_value=state),
    )
    renderer = SimpleNamespace(
        start=AsyncMock(),
        close=AsyncMock(),
        browser=SimpleNamespace(new_context=AsyncMock(return_value=context)),
        _capture=AsyncMock(side_effect=None if reuse_ok else ValueError("FAILED")),
    )
    monkeypatch.setattr(tool, "IssuerRenderer", lambda: renderer)
    monkeypatch.setattr(tool, "inspect_terms", AsyncMock(return_value=terms_digest(TERMS)))
    monkeypatch.setattr(tool, "inspect_form", AsyncMock(return_value={"accept_control_count": 1}))
    choices = AsyncMock()
    monkeypatch.setattr(tool, "apply_choices", choices)
    saved = []
    monkeypatch.setattr(tool, "save_consent", lambda *a: saved.append(a))
    _, digest = terms_digest(TERMS)
    if reuse_ok:
        result = await tool.setup(
            confirm=digest, accepted=True, eligibility_confirmed=True, remember=True
        )
        assert result["status"] == "CONSENT_STORED_PRODUCT_VERIFIED" and len(saved) == 1
    else:
        with pytest.raises(ValueError, match="FAILED"):
            await tool.setup(
                confirm=digest, accepted=True, eligibility_confirmed=True, remember=True
            )
        assert saved == []
    control.click.assert_awaited_once()
    choices.assert_awaited_once_with(page, accepted=True, eligibility_confirmed=True, remember=True)
    renderer._capture.assert_awaited_once_with("JPMORGAN", ISIN, URL, consent_override=state)

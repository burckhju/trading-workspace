"""Regression using the three actual text states from the failed operator run."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.tools import setup_jpmorgan_consent as setup

FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[3] / "fixtures/jpmorgan/consent-presentation-20260930.json"
    ).read_text(encoding="utf-8")
)
REVIEWED = FIXTURE["reviewed_text"]
REVIEWED_HASH = FIXTURE["reviewed_sha256"]
DISPLAYED = FIXTURE["display_states"][-1]["terms_text"]


@pytest.mark.parametrize("row", FIXTURE["display_states"], ids=lambda row: row["stage"])
def test_actual_text_states_keep_exact_reviewed_terms_and_hash(row: dict[str, str]) -> None:
    normalized, digest = setup.terms_digest(row["terms_text"])
    assert normalized == REVIEWED
    assert digest == REVIEWED_HASH


@pytest.mark.parametrize("button", ["", " Einverstanden", " EINVERSTANDEN"])
@pytest.mark.parametrize("cookie_banner", [False, True])
def test_observed_button_and_cookie_visibility_variants(button: str, cookie_banner: bool) -> None:
    shown = REVIEWED.removesuffix(" Back to top") + button + " Back to top"
    if cookie_banner:
        shown += " " + setup.COOKIE_NOTICE_TEXT
    assert setup.terms_digest(shown) == (REVIEWED, REVIEWED_HASH)


@pytest.mark.parametrize(
    "changed",
    [
        DISPLAYED.replace("22. Januar 2022", "23. Januar 2022"),
        DISPLAYED.replace(
            "Hiermit bestätigte ich", "Eine zusätzliche Bedingung. Hiermit bestätigte ich"
        ),
        DISPLAYED.replace("keine US-Person", "eine US-Person"),
        DISPLAYED.replace("stimme ihnen zu.", "stimme ihnen teilweise zu."),
        DISPLAYED.replace("für 30 Tage", "für 60 Tage"),
        DISPLAYED.replace("EINVERSTANDEN", "EINVERSTANDEN Neue Bedingung."),
        DISPLAYED + " Zusätzliche Bedingung nach dem Cookie-Banner.",
        DISPLAYED.replace("Marketingbemühungen", "Zusatzbedingungen"),
        DISPLAYED.replace("EINVERSTANDEN", "Einverstanden Einverstanden"),
        REVIEWED.replace(
            "Hiermit bestätigte ich", setup.COOKIE_NOTICE_TEXT + " Hiermit bestätigte ich"
        ),
    ],
)
def test_legal_declaration_and_unknown_display_changes_still_block(changed: str) -> None:
    _, digest = setup.terms_digest(changed)
    assert digest != REVIEWED_HASH
    with pytest.raises(ValueError, match="CONFIRMATION_MISSING_OR_CHANGED"):
        setup.require_confirmation(digest, REVIEWED_HASH, True)


@pytest.mark.asyncio
async def test_cookie_banner_arriving_during_text_read_is_rejected_and_reread() -> None:
    reject = SimpleNamespace(
        count=AsyncMock(return_value=1),
        is_visible=AsyncMock(side_effect=[False, True, True, False]),
        click=AsyncMock(),
        wait_for=AsyncMock(),
    )
    body = SimpleNamespace(inner_text=AsyncMock(side_effect=[DISPLAYED, REVIEWED]))
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value=None),
        get_by_role=lambda *args, **kwargs: reject,
        locator=lambda selector: body,
    )
    assert await setup.inspect_terms(page) == (REVIEWED, REVIEWED_HASH)
    reject.click.assert_awaited_once_with(timeout=3000)
    reject.wait_for.assert_awaited_once_with(state="hidden", timeout=5000)
    assert body.inner_text.await_count == 2


@pytest.mark.asyncio
async def test_persistent_cookie_overlay_aborts_before_final_submit() -> None:
    reject = SimpleNamespace(
        count=AsyncMock(return_value=1),
        is_visible=AsyncMock(return_value=True),
        click=AsyncMock(),
        wait_for=AsyncMock(side_effect=setup.BrowserTimeout("private browser call log")),
    )
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value=None),
        get_by_role=lambda *args, **kwargs: reject,
        locator=lambda selector: SimpleNamespace(inner_text=AsyncMock(return_value=DISPLAYED)),
    )
    with pytest.raises(setup.CookieBannerNotDismissed) as caught:
        await setup.inspect_terms(page)
    assert reject.click.await_count == 2
    assert reject.wait_for.await_count == 2
    assert caught.value.diagnostics == {
        "cookie_reject_attempts": ["STILL_VISIBLE_AFTER_WAIT", "STILL_VISIBLE_AFTER_WAIT"],
        "wait_after_each_click_ms": 5000,
    }
    assert "private" not in json.dumps(caught.value.diagnostics)


@pytest.mark.asyncio
async def test_read_waits_for_dismissal_instead_of_clicking_twice() -> None:
    visible = True
    events: list[str] = []

    async def click(**kwargs: object) -> None:
        events.append("clicked")
        # The UI remains visible after the click until its async dismissal ends.

    async def wait_for(**kwargs: object) -> None:
        nonlocal visible
        assert visible
        events.append("dismissal_wait")
        visible = False

    async def body_text(**kwargs: object) -> str:
        assert not visible, "Terms must be read after the dismissal wait"
        events.append("read_terms")
        return REVIEWED

    reject = SimpleNamespace(
        count=AsyncMock(return_value=1),
        is_visible=AsyncMock(side_effect=lambda: visible),
        click=AsyncMock(side_effect=click),
        wait_for=AsyncMock(side_effect=wait_for),
    )
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value=None),
        get_by_role=lambda *args, **kwargs: reject,
        locator=lambda selector: SimpleNamespace(inner_text=AsyncMock(side_effect=body_text)),
    )
    assert await setup.inspect_terms(page) == (REVIEWED, REVIEWED_HASH)
    assert events == ["clicked", "dismissal_wait", "read_terms"]
    reject.click.assert_awaited_once()


@pytest.mark.asyncio
async def test_one_bounded_retry_can_finish_dismissal() -> None:
    reject = SimpleNamespace(
        count=AsyncMock(return_value=1),
        is_visible=AsyncMock(side_effect=[True, True, False]),
        click=AsyncMock(),
        wait_for=AsyncMock(side_effect=[setup.BrowserTimeout("ignored"), None]),
    )
    body = SimpleNamespace(inner_text=AsyncMock(return_value=REVIEWED))
    page = SimpleNamespace(
        evaluate=AsyncMock(return_value=None),
        get_by_role=lambda *args, **kwargs: reject,
        locator=lambda selector: body,
    )
    assert await setup.inspect_terms(page) == (REVIEWED, REVIEWED_HASH)
    assert reject.click.await_count == 2
    body.inner_text.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("changed_legal_text", [False, True])
async def test_three_stage_setup_accepts_only_original_reviewed_legal_text(
    monkeypatch: pytest.MonkeyPatch, changed_legal_text: bool
) -> None:
    control = SimpleNamespace(
        click=AsyncMock(), evaluate=AsyncMock(return_value=None), wait_for=AsyncMock()
    )
    page = SimpleNamespace(
        main_frame=object(),
        url="https://www.jpmorgan-zertifikate.de/zertifikate-detail/DE000JZ91459",
        goto=AsyncMock(return_value=SimpleNamespace(status=200)),
        locator=lambda *args: control,
        evaluate=AsyncMock(return_value="<product/>"),
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
        _capture=AsyncMock(),
    )
    monkeypatch.setattr(setup, "IssuerRenderer", lambda: renderer)
    text_states = [row["terms_text"] for row in FIXTURE["display_states"]]
    if changed_legal_text:
        text_states[-1] = text_states[-1].replace("22. Januar 2022", "23. Januar 2022")
    monkeypatch.setattr(
        setup,
        "inspect_terms",
        AsyncMock(side_effect=[setup.terms_digest(text) for text in text_states]),
    )
    monkeypatch.setattr(setup, "inspect_form", AsyncMock(return_value={"accept_control_count": 1}))
    monkeypatch.setattr(setup, "apply_choices", AsyncMock())
    monkeypatch.setattr(setup, "parse_product_page", lambda *args: object())
    saved = []
    monkeypatch.setattr(setup, "save_consent", lambda *args: saved.append(args))
    if changed_legal_text:
        with pytest.raises(ValueError, match="CONFIRMATION_MISSING_OR_CHANGED"):
            await setup.setup(
                confirm=REVIEWED_HASH, accepted=True, eligibility_confirmed=True, remember=True
            )
        control.click.assert_not_awaited()
        assert saved == []
    else:
        result = await setup.setup(
            confirm=REVIEWED_HASH, accepted=True, eligibility_confirmed=True, remember=True
        )
        assert result["status"] == "CONSENT_STORED_PRODUCT_VERIFIED"
        assert result["terms_sha256"] == REVIEWED_HASH
        control.click.assert_awaited_once()
        renderer._capture.assert_awaited_once()
        assert saved[0][1] == REVIEWED_HASH

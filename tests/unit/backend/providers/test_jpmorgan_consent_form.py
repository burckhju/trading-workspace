"""Observed hidden inputs, visible labels and explicit operator declarations."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.providers.issuer_renderer import consent_form as form
from app.tools import setup_jpmorgan_consent as setup


class FormPage:
    """DOM relationship mock: hidden native inputs and associated visible labels."""

    def __init__(self) -> None:
        self.checked = dict.fromkeys(form.STATEMENTS, False)
        self.labels = {}
        self.controls = {}
        self.clicked: list[str] = []
        for identity, statement in form.STATEMENTS.items():
            control = SimpleNamespace(
                count=AsyncMock(return_value=1),
                is_enabled=AsyncMock(return_value=True),
                is_checked=AsyncMock(side_effect=lambda key=identity: self.checked[key]),
            )
            label = SimpleNamespace(
                count=AsyncMock(return_value=1),
                text_content=AsyncMock(return_value=statement),
                is_visible=AsyncMock(return_value=True),
            )

            async def click(*, timeout: int, key: str = identity) -> None:
                assert timeout == 5000
                self.checked[key] = not self.checked[key]
                self.clicked.append(key)

            label.click = AsyncMock(side_effect=click)
            label.or_ = lambda other, own=label: own
            self.controls[identity] = control
            self.labels[identity] = label
        self.submit = SimpleNamespace(
            count=AsyncMock(return_value=1),
            text_content=AsyncMock(return_value="Einverstanden"),
            is_visible=AsyncMock(return_value=False),
            click=AsyncMock(),
        )

    def locator(self, selector: str) -> object:
        if selector == form.SUBMIT_SELECTOR:
            return self.submit
        if selector == "label":
            return SimpleNamespace(filter=lambda **kwargs: object())
        for identity in form.STATEMENTS:
            if selector == f'input[type="checkbox"][id="{identity}"]':
                return self.controls[identity]
            if selector == f'label[for="{identity}"]':
                return self.labels[identity]
        raise AssertionError(selector)


@pytest.mark.asyncio
async def test_hidden_accept_link_is_recognized_without_any_selection() -> None:
    page = FormPage()
    result = await form.inspect_form(page)
    assert result["accept_control_count"] == 1 and result["accept_visible"] is False
    assert page.clicked == []
    page.submit.click.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("accepted,eligible", [(False, False), (False, True), (True, False)])
async def test_no_declaration_without_both_explicit_flags(accepted: bool, eligible: bool) -> None:
    page = FormPage()
    with pytest.raises(ValueError, match="EXPLICIT_ELIGIBILITY"):
        await form.apply_choices(
            page, accepted=accepted, eligibility_confirmed=eligible, remember=True
        )
    assert page.clicked == []


@pytest.mark.asyncio
@pytest.mark.parametrize("remember", [False, True])
async def test_hidden_native_inputs_use_labels_and_remember_is_explicit(remember: bool) -> None:
    page = FormPage()
    await form.apply_choices(page, accepted=True, eligibility_confirmed=True, remember=remember)
    assert page.checked == {
        form.RESIDENCE_ID: True,
        form.TERMS_ID: True,
        form.REMEMBER_ID: remember,
    }
    assert page.clicked[:2] == [form.RESIDENCE_ID, form.TERMS_ID]
    page.submit.click.assert_not_awaited()


@pytest.mark.asyncio
async def test_altered_residence_statement_blocks_without_clicking() -> None:
    page = FormPage()
    page.labels[form.RESIDENCE_ID].text_content.return_value = "A materially different statement"
    with pytest.raises(ValueError, match="STATEMENT_CHANGED"):
        await form.inspect_form(page)
    assert page.clicked == []


@pytest.mark.asyncio
async def test_label_click_must_change_native_checkbox_state() -> None:
    page = FormPage()
    page.labels[form.RESIDENCE_ID].click = AsyncMock()
    with pytest.raises(ValueError, match="STATE_NOT_CONFIRMED"):
        await form.apply_choices(page, accepted=True, eligibility_confirmed=True, remember=False)
    page.labels[form.TERMS_ID].click.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_declaration_stops_before_browser_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Mock()
    monkeypatch.setattr(setup, "IssuerRenderer", factory)
    with pytest.raises(ValueError, match="EXPLICIT_ELIGIBILITY"):
        await setup.setup(confirm="a" * 64, accepted=True)
    factory.assert_not_called()


def test_submit_visibility_does_not_change_terms_hash_but_legal_text_does() -> None:
    text = (
        "WICHTIGE HINWEISE UND NUTZUNGSBEDINGUNGEN "
        "Die Nutzung dieser Website ist nur Nutzern gestattet, welche "
        "die Zustimmung durch Anklicken des Bestätigungsbuttons erteilen. "
        "Einstellungen merken (für 30 Tage) Back to top"
    )
    shown = text.replace(" Back to top", " Einverstanden Back to top")
    assert setup.terms_digest(text) == setup.terms_digest(shown)
    assert setup.terms_digest(text) != setup.terms_digest(
        text.replace("erteilen.", "erteilen. Eine zusätzliche Bedingung.")
    )

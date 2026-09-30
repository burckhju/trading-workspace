"""JPMorgan form observed on 2026-09-30; no choices without operator approval.

Native checkboxes are visually hidden by the site. Use their associated visible
labels and verify the actual checked state, never force clicks or mutate the DOM.
"""

from __future__ import annotations

from playwright.async_api import Locator, Page

RESIDENCE_ID = "CheckBoxNotUsResidential"
TERMS_ID = "CheckBoxTermsOfService"
REMEMBER_ID = "CheckBoxSaveSettings"
STATEMENTS = {
    RESIDENCE_ID: (
        "Hiermit bestätigte ich, (i) dass ich meinen Wohnsitz in der Bundesrepublik "
        "Deutschland oder der Republik Österreich habe, (ii) dass ich meinen Wohnsitz "
        "nicht in den Vereinigten Staaten habe und (iii) dass ich keine US-Person bin."
    ),
    TERMS_ID: "Ich habe die Nutzungsbedingungen zur Kenntnis genommen und stimme ihnen zu.",
    REMEMBER_ID: "Einstellungen merken (für 30 Tage)",
}
SUBMIT_SELECTOR = "a#AcceptButton"
SUBMIT_TEXT = "Einverstanden"


def normalize(text: str | None) -> str:
    return " ".join((text or "").split())


async def checkbox_and_label(page: Page, identity: str) -> tuple[Locator, Locator]:
    control = page.locator(f'input[type="checkbox"][id="{identity}"]')
    if await control.count() != 1:
        raise ValueError("JPMORGAN_CHECKBOX_MISSING_OR_AMBIGUOUS")
    label = page.locator(f'label[for="{identity}"]').or_(page.locator("label").filter(has=control))
    if await label.count() != 1:
        raise ValueError("JPMORGAN_CHECKBOX_LABEL_MISSING_OR_AMBIGUOUS")
    if normalize(await label.text_content()) != STATEMENTS[identity]:
        raise ValueError("JPMORGAN_CHECKBOX_STATEMENT_CHANGED")
    if not await label.is_visible() or not await control.is_enabled():
        raise ValueError("JPMORGAN_CHECKBOX_NOT_INTERACTIVE")
    return control, label


async def inspect_form(page: Page) -> dict[str, object]:
    fields = []
    for identity in STATEMENTS:
        control, _ = await checkbox_and_label(page, identity)
        fields.append(
            {
                "id": identity,
                "statement": STATEMENTS[identity],
                "checked": await control.is_checked(),
            }
        )
    submit = page.locator(SUBMIT_SELECTOR)
    count = await submit.count()
    if count != 1 or normalize(await submit.text_content()) != SUBMIT_TEXT:
        raise ValueError("JPMORGAN_ACCEPT_CONTROL_MISSING_OR_CHANGED")
    return {
        "schema_version": "JPMORGAN_CHECKBOX_FORM_V1",
        "checkboxes": fields,
        "accept_control_count": count,
        "accept_text": SUBMIT_TEXT,
        "accept_visible": await submit.is_visible(),
    }


async def choose_option(page: Page, identity: str, checked: bool) -> None:
    control, label = await checkbox_and_label(page, identity)
    if await control.is_checked() != checked:
        await label.click(timeout=5000)
    if await control.is_checked() != checked:
        raise ValueError("JPMORGAN_CHECKBOX_STATE_NOT_CONFIRMED")


async def apply_choices(
    page: Page, *, accepted: bool, eligibility_confirmed: bool, remember: bool
) -> None:
    if not accepted or not eligibility_confirmed:
        raise ValueError("JPMORGAN_EXPLICIT_ELIGIBILITY_CONFIRMATION_REQUIRED")
    await choose_option(page, RESIDENCE_ID, True)
    await choose_option(page, TERMS_ID, True)
    await choose_option(page, REMEMBER_ID, remember)
    for identity, expected in ((RESIDENCE_ID, True), (TERMS_ID, True), (REMEMBER_ID, remember)):
        control, _ = await checkbox_and_label(page, identity)
        if await control.is_checked() != expected:
            raise ValueError("JPMORGAN_CHECKBOX_STATE_NOT_CONFIRMED")

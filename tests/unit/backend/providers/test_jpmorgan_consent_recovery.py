"""Recover saved consent without accepting again; diagnose timeouts without secrets."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from playwright.async_api import TimeoutError as BrowserTimeout

from app.providers.issuer_renderer import consent_state
from app.tools import setup_jpmorgan_consent as setup

DIGEST = "5b91cb6c6b389362df312b3f4fdf72fddb36e407a67f1c73b6d4433c011f3d1b"
SECRET = "cookie-storage-and-url-secret"
STATE = {
    "cookies": [
        {
            "domain": ".jpmorgan-zertifikate.de",
            "name": "consent",
            "value": SECRET,
        }
    ],
    "origins": [],
}


@pytest.fixture
def environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "state.json"
    monkeypatch.setattr(setup, "STATE_PATH", path)
    renderer = SimpleNamespace(
        start=AsyncMock(),
        close=AsyncMock(),
        _capture=AsyncMock(),
        browser=SimpleNamespace(new_context=AsyncMock()),
    )
    factory = Mock(return_value=renderer)
    monkeypatch.setattr(setup, "IssuerRenderer", factory)
    choices = AsyncMock()
    monkeypatch.setattr(setup, "apply_choices", choices)
    writes = Mock(side_effect=lambda state, digest: consent_state.save_consent(state, digest, path))
    monkeypatch.setattr(setup, "save_consent", writes)
    return SimpleNamespace(
        path=path, renderer=renderer, factory=factory, writes=writes, choices=choices
    )


async def accept(trace=None):
    return await setup.setup(
        confirm=DIGEST, accepted=True, eligibility_confirmed=True, remember=True, trace=trace
    )


@pytest.mark.asyncio
async def test_saved_state_is_reused_without_new_acceptance_or_write(environment):
    consent_state.save_consent(STATE, DIGEST, environment.path)
    before = environment.path.read_bytes()
    result = await accept()
    assert result["status"] == "EXISTING_CONSENT_REUSE_VERIFIED"
    assert result["new_acceptance_performed"] is False
    assert result["product_reuse_verified"] is True
    environment.renderer.browser.new_context.assert_not_awaited()
    environment.renderer._capture.assert_awaited_once_with(
        "JPMORGAN",
        setup.ISIN,
        "https://www.jpmorgan-zertifikate.de/zertifikate-detail/" + setup.ISIN,
        consent_override=STATE,
    )
    environment.choices.assert_not_awaited()
    environment.writes.assert_not_called()
    assert environment.path.read_bytes() == before
    diagnostics = result["setup_diagnostics"]
    assert diagnostics["stored_state_before"]["reviewed_terms_match"] is True
    assert diagnostics["stored_state_after"]["valid"] is True
    assert SECRET not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", ["broken-json", "other-hash"])
async def test_invalid_or_different_saved_consent_is_preserved_before_browser(environment, stored):
    if stored == "broken-json":
        environment.path.write_text(SECRET)
    else:
        consent_state.save_consent(STATE, "a" * 64, environment.path)
    before = environment.path.read_bytes()
    trace = setup.SetupTrace()
    with pytest.raises(ValueError):
        await accept(trace)
    environment.factory.assert_not_called()
    environment.writes.assert_not_called()
    assert environment.path.read_bytes() == before
    assert SECRET not in json.dumps(trace.report())


@pytest.mark.asyncio
async def test_expired_saved_consent_does_not_silently_accept_again(environment):
    consent_state.save_consent(STATE, DIGEST, environment.path)
    before = environment.path.read_bytes()
    environment.renderer._capture.side_effect = ValueError("ISSUER_RENDER_TERMS_REQUIRED")
    trace = setup.SetupTrace()
    with pytest.raises(ValueError, match="ISSUER_RENDER_TERMS_REQUIRED"):
        await accept(trace)
    environment.renderer.browser.new_context.assert_not_awaited()
    environment.choices.assert_not_awaited()
    environment.writes.assert_not_called()
    assert environment.path.read_bytes() == before
    assert any(
        row["phase"] == "VERIFY_EXISTING_STATE_IN_FRESH_CONTEXT" and row["outcome"] == "FAILED"
        for row in trace.steps
    )


@pytest.mark.asyncio
async def test_browser_timeout_and_cleanup_failure_keep_original_error(environment):
    environment.renderer.start.side_effect = BrowserTimeout(
        "Page.goto: Timeout 20000ms exceeded.\nCall log: https://private.test/?token=" + SECRET
    )
    environment.renderer.close.side_effect = TimeoutError(SECRET)
    trace = setup.SetupTrace()
    with pytest.raises(BrowserTimeout):
        await accept(trace)
    result = trace.report()
    failed = [row for row in result["steps"] if row["outcome"] == "FAILED"]
    assert [row["phase"] for row in failed] == ["BROWSER_START", "CLEANUP_RENDERER"]
    error = result["error_chain"][0]
    assert error["browser_operation"] == "Page.goto"
    assert error["timeout_ms"] == 20000
    assert error["app_frames"]
    assert result["stored_state_after"]["status"] == "NOT_CONFIGURED"
    assert SECRET not in json.dumps(result)
    assert "private.test" not in json.dumps(result)


@pytest.mark.asyncio
async def test_overall_deadline_identifies_cancelled_phase(environment, monkeypatch):
    async def wait_forever():
        await asyncio.Event().wait()

    monkeypatch.setattr(setup, "SETUP_TIMEOUT_SECONDS", 0.01)
    environment.renderer.start.side_effect = wait_forever
    trace = setup.SetupTrace()
    with pytest.raises(TimeoutError):
        await accept(trace)
    failed = next(row for row in trace.steps if row["phase"] == "BROWSER_START")
    assert failed["outcome"] == "CANCELLED"
    assert failed["elapsed_seconds"] >= 0.001
    assert trace.error_chain[0]["type"] == "TimeoutError"
    assert any(row["type"] == "CancelledError" for row in trace.error_chain)
    environment.renderer.close.assert_awaited_once()


def acceptance_page(environment, monkeypatch):
    control = SimpleNamespace(
        evaluate=AsyncMock(return_value=None), wait_for=AsyncMock(), click=AsyncMock()
    )
    page = SimpleNamespace(
        main_frame=object(),
        url="https://www.jpmorgan-zertifikate.de/zertifikate-detail/" + setup.ISIN,
        goto=AsyncMock(return_value=SimpleNamespace(status=200)),
        locator=lambda _: control,
        evaluate=AsyncMock(return_value="<product/>"),
    )
    context = SimpleNamespace(
        new_page=AsyncMock(return_value=page),
        route=AsyncMock(),
        route_web_socket=AsyncMock(),
        close=AsyncMock(),
        storage_state=AsyncMock(return_value=STATE),
    )
    environment.renderer.browser.new_context.return_value = context
    monkeypatch.setattr(setup, "inspect_terms", AsyncMock(return_value=("reviewed text", DIGEST)))
    monkeypatch.setattr(setup, "inspect_form", AsyncMock(return_value={"accept_control_count": 1}))
    monkeypatch.setattr(setup, "parse_product_page", lambda *args: object())
    return context, control


@pytest.mark.asyncio
async def test_post_save_cleanup_timeout_reports_saved_state_and_next_run_reuses(
    environment, monkeypatch
):
    _, control = acceptance_page(environment, monkeypatch)
    environment.renderer.close.side_effect = TimeoutError(SECRET)
    trace = setup.SetupTrace()
    with pytest.raises(TimeoutError):
        await accept(trace)
    assert trace.before["status"] == "NOT_CONFIGURED"
    assert trace.after["status"] == "STORED"
    assert trace.after["reviewed_terms_match"] is True
    assert consent_state.load_consent(environment.path) == STATE
    environment.writes.assert_called_once()
    control.click.assert_awaited_once()
    environment.renderer.close.side_effect = None
    second = await accept()
    assert second["status"] == "EXISTING_CONSENT_REUSE_VERIFIED"
    environment.writes.assert_called_once()
    control.click.assert_awaited_once()
    assert SECRET not in json.dumps(trace.report())


@pytest.mark.asyncio
async def test_context_close_does_not_replace_submission_failure(environment, monkeypatch):
    context, control = acceptance_page(environment, monkeypatch)
    control.click.side_effect = BrowserTimeout("Locator.click: Timeout 5000ms exceeded. " + SECRET)
    context.close.side_effect = TimeoutError(SECRET)
    trace = setup.SetupTrace()
    with pytest.raises(BrowserTimeout):
        await accept(trace)
    assert trace.error_chain[0]["browser_operation"] == "Locator.click"
    assert trace.after["status"] == "NOT_CONFIGURED"
    assert any(
        row["phase"] == "CLEANUP_ACCEPTANCE_CONTEXT" and row["outcome"] == "FAILED"
        for row in trace.steps
    )
    environment.writes.assert_not_called()


def test_cli_failure_includes_sanitized_trace_and_nonzero_exit(environment, monkeypatch, capsys):
    environment.renderer.start.side_effect = BrowserTimeout(
        "BrowserType.launch: Timeout 20000ms exceeded. " + SECRET
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "setup",
            "--accept-current-jpmorgan-terms",
            "--confirm-sha256",
            DIGEST,
            "--confirm-de-at-residence-and-non-us-person",
            "--remember-30-days",
        ],
    )
    with pytest.raises(SystemExit) as stopped:
        setup.main()
    assert stopped.value.code == 2
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status"] == "SETUP_NOT_COMPLETED"
    assert (
        result["setup_diagnostics"]["error_chain"][0]["browser_operation"] == "BrowserType.launch"
    )
    assert SECRET not in output

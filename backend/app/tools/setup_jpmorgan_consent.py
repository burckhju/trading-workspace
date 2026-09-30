"""Explicit operator-only terms setup. Unattended renderer requests never call this tool."""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

from playwright.async_api import Page, Route, StorageState, WebSocketRoute
from playwright.async_api import TimeoutError as BrowserTimeout

from app.features.market_data.domain.issuer_route_evidence import allowed_product_url, product_url
from app.providers.issuer_pages import is_jpmorgan_terms_page, parse_product_page
from app.providers.issuer_renderer.browser import (
    ACCESS_STATE,
    SANITIZED_DOM,
    IssuerRenderer,
    allowed_resource,
)
from app.providers.issuer_renderer.consent_form import (
    REMEMBER_ID,
    STATEMENTS,
    SUBMIT_SELECTOR,
    TERMS_ID,
    apply_choices,
    inspect_form,
)
from app.providers.issuer_renderer.consent_state import (
    STATE_PATH,
    load_consent,
    restrict_state,
    save_consent,
)

ISIN = "DE000JZ91459"
COOKIE_NOTICE_TEXT = (
    "Wenn Sie auf „Alle Cookies akzeptieren“ klicken, stimmen Sie der Speicherung "
    "von Cookies auf Ihrem Gerät zu, um die Websitenavigation zu verbessern, "
    "die Websitenutzung zu analysieren und unsere Marketingbemühungen zu unterstützen. "
    "Cookie-Einstellungen Alle ablehnen Alle Cookies akzeptieren"
)
COOKIE_DISMISS_TIMEOUT_MS = 5000
SETUP_TIMEOUT_SECONDS = 90


def error_details(exc: BaseException) -> list[dict[str, object]]:
    """Report code locations and timeout operations, never raw browser call logs."""
    rows: list[dict[str, object]] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen and len(rows) < 6:
        seen.add(id(current))
        frames: list[dict[str, object]] = []
        trace = current.__traceback__
        while trace is not None:
            filename = trace.tb_frame.f_code.co_filename
            module = None
            if filename.startswith("/app/app/"):
                module = filename.removeprefix("/app/")
            elif Path(filename).name == "setup_jpmorgan_consent.py":
                module = "app/tools/setup_jpmorgan_consent.py"
            if module is not None:
                frames.append(
                    {
                        "module": module,
                        "function": trace.tb_frame.f_code.co_name,
                        "line": trace.tb_lineno,
                    }
                )
            trace = trace.tb_next
        row: dict[str, object] = {"type": type(current).__name__, "app_frames": frames[-10:]}
        message = str(current)
        if re.fullmatch(r"[A-Z][A-Z0-9_]{1,100}", message):
            row["reason_code"] = message
        timeout = re.match(r"([A-Za-z]+\.[A-Za-z_]+): Timeout (\d+)ms exceeded\.?", message)
        if timeout:
            row["browser_operation"] = timeout.group(1)
            row["timeout_ms"] = int(timeout.group(2))
        rows.append(row)
        current = current.__cause__ or current.__context__
    return rows


def stored_state_metadata(confirm: str | None) -> dict[str, object]:
    """Inspect the local record without exposing any cookie or storage value."""
    try:
        if STATE_PATH.is_symlink():
            return {"status": "SYMLINK", "valid": False}
        state = load_consent(STATE_PATH)
        if state is None:
            return {"status": "NOT_CONFIGURED", "valid": False}
        record = json.loads(STATE_PATH.read_text())
        return {
            "status": "STORED",
            "valid": True,
            "record_bytes": STATE_PATH.stat().st_size,
            "reviewed_terms_match": record["terms_sha256"] == confirm,
            **state_metrics(state),
        }
    except Exception as exc:
        # Metadata must not replace the actual setup error.
        return {
            "status": "INVALID_OR_UNREADABLE",
            "valid": False,
            "error_chain": error_details(exc),
        }


class SetupTrace:
    """One in-memory trace per setup; no HTML, URLs or storage values."""

    def __init__(self) -> None:
        self.started = monotonic()
        self.started_at = datetime.now(UTC).isoformat()
        self.steps: list[dict[str, object]] = []
        self.before: dict[str, object] = {}
        self.after: dict[str, object] = {}
        self.error_chain: list[dict[str, object]] = []

    def report(self) -> dict[str, object]:
        return {
            "schema_version": "JPMORGAN_CONSENT_PHASE_TRACE_V1",
            "started_at": self.started_at,
            "elapsed_seconds": round(monotonic() - self.started, 3),
            "setup_timeout_seconds": SETUP_TIMEOUT_SECONDS,
            "steps": self.steps.copy(),
            "stored_state_before": self.before,
            "stored_state_after": self.after,
            "error_chain": self.error_chain,
        }


CURRENT_TRACE: ContextVar[SetupTrace | None] = ContextVar("jpmorgan_setup_trace", default=None)


@contextmanager
def traced_step(name: str) -> Iterator[None]:
    trace = CURRENT_TRACE.get()
    if trace is None:
        yield
        return
    started = monotonic()
    row: dict[str, object] = {
        "phase": name,
        "started_after_seconds": round(started - trace.started, 3),
        "outcome": "RUNNING",
    }
    trace.steps.append(row)
    try:
        yield
    except BaseException as exc:
        row["outcome"] = "CANCELLED" if isinstance(exc, asyncio.CancelledError) else "FAILED"
        row["error_chain"] = error_details(exc)
        raise
    else:
        row["outcome"] = "COMPLETED"
    finally:
        row["elapsed_seconds"] = round(monotonic() - started, 3)


class CookieBannerNotDismissed(ValueError):
    """Public diagnostics only: never store browser messages, cookies or URLs."""

    def __init__(self, attempts: list[str]) -> None:
        super().__init__("JPMORGAN_COOKIE_BANNER_NOT_DISMISSED")
        self.diagnostics: dict[str, object] = {
            "cookie_reject_attempts": attempts.copy(),
            "wait_after_each_click_ms": COOKIE_DISMISS_TIMEOUT_MS,
        }


class ConsentStateNotStored(ValueError):
    """Storage failure with counts and byte sizes, never storage values."""

    def __init__(self, reason: str, diagnostics: dict[str, object]) -> None:
        super().__init__(reason)
        self.diagnostics = diagnostics


def state_metrics(state: StorageState) -> dict[str, int]:
    return {
        "storage_state_json_bytes": len(json.dumps(state).encode()),
        "cookie_count": len(state["cookies"]),
        "origin_count": len(state["origins"]),
        "local_storage_entry_count": sum(
            len(origin["localStorage"]) for origin in state["origins"]
        ),
    }


async def verify_and_save_consent(
    renderer: IssuerRenderer, state: StorageState, digest: str, isin: str, url: str
) -> dict[str, object]:
    """Keep the installed writer and size cap; verify any smaller state anew."""
    diagnostics: dict[str, object] = {"full_scoped_state": state_metrics(state)}
    if STATE_PATH.is_symlink():
        raise ConsentStateNotStored("ISSUER_CONSENT_DESTINATION_SYMLINK", diagnostics)
    with traced_step("VERIFY_FULL_STATE_IN_FRESH_CONTEXT"):
        await renderer._capture("JPMORGAN", isin, url, consent_override=state)
    diagnostics["full_state_product_reuse_verified"] = True
    try:
        with traced_step("SAVE_FULL_STATE"):
            save_consent(state, digest)
    except ValueError as exc:
        if str(exc) != "ISSUER_CONSENT_STATE_INVALID":
            raise
        diagnostics["full_state_writer_rejection"] = str(exc)
        if STATE_PATH.is_symlink():
            raise ConsentStateNotStored("ISSUER_CONSENT_DESTINATION_SYMLINK", diagnostics) from None
        # The version-checked writer rejects this state before writing if its
        # record is oversized. Do not raise its limit or guess localStorage keys.
        minimal: StorageState = {"cookies": state["cookies"], "origins": []}
        diagnostics["cookie_only_state"] = state_metrics(minimal)
        if not state["origins"] or not state["cookies"]:
            raise ConsentStateNotStored(
                "ISSUER_CONSENT_NO_SMALLER_COOKIE_STATE", diagnostics
            ) from None
        try:
            # Real product/terms-gate verification using only the captured
            # JPMorgan cookies in another fresh context. Never synthesize cookies.
            with traced_step("VERIFY_COOKIE_ONLY_STATE_IN_FRESH_CONTEXT"):
                await renderer._capture("JPMORGAN", isin, url, consent_override=minimal)
        except Exception as reuse_error:
            diagnostics["cookie_only_reuse_error_type"] = type(reuse_error).__name__
            message = str(reuse_error)
            if re.fullmatch(r"[A-Z][A-Z0-9_]{1,100}", message):
                diagnostics["cookie_only_reuse_reason"] = message
            raise ConsentStateNotStored(
                "ISSUER_CONSENT_COOKIE_ONLY_REUSE_FAILED", diagnostics
            ) from None
        diagnostics["cookie_only_product_reuse_verified"] = True
        try:
            with traced_step("SAVE_COOKIE_ONLY_STATE"):
                save_consent(minimal, digest)
        except ValueError as store_error:
            if str(store_error) != "ISSUER_CONSENT_STATE_INVALID":
                raise
            raise ConsentStateNotStored(
                "ISSUER_CONSENT_COOKIE_ONLY_NOT_STORED", diagnostics
            ) from None
        mode = "SCOPED_COOKIES_ONLY_VERIFIED"
    else:
        mode = "FULL_SCOPED_STATE_VERIFIED"
    return {"consent_storage_mode": mode, "consent_storage_diagnostics": diagnostics}


def _normalize_terms_presentation(text: str) -> str:
    """Exclude only the exact display additions captured on 2026-09-30.

    Keep the entire terms/declaration text and the reviewed hash. Unknown banner
    text, new clauses, changed declarations and additions elsewhere stay hashed.
    """
    text = " ".join(text.split())
    notice_suffix = " " + COOKIE_NOTICE_TEXT
    if text.endswith(notice_suffix):
        without_notice = text[: -len(notice_suffix)]
        declaration_tail = f"{STATEMENTS[TERMS_ID]} {STATEMENTS[REMEMBER_ID]}"
        if any(
            without_notice.endswith(f"{declaration_tail}{button} Back to top")
            for button in ("", " Einverstanden", " EINVERSTANDEN")
        ):
            text = without_notice
    # CSS text-transform changes inner_text() to uppercase once the link shows.
    # Both spellings are excluded only at the exact previously observed form tail.
    return re.sub(
        r"(Einstellungen merken \(für 30 Tage\)) (?:Einverstanden|EINVERSTANDEN)"
        r"(?= Back to top$|$)",
        r"\1",
        text,
    )


def terms_digest(text: str) -> tuple[str, str]:
    text = _normalize_terms_presentation(text)
    start = text.casefold().find("wichtige hinweise und nutzungsbedingungen")
    if start < 0 or not is_jpmorgan_terms_page(text, has_product_bindings=False):
        raise ValueError("JPMORGAN_TERMS_PAGE_NOT_RECOGNIZED")
    text = text[start:]
    if len(text) > 100_000:
        raise ValueError("JPMORGAN_TERMS_PAGE_TOO_LARGE")
    return text, hashlib.sha256(text.encode()).hexdigest()


def require_confirmation(actual: str, expected: str | None, accepted: bool) -> None:
    if not accepted or expected != actual or not re.fullmatch(r"[a-f0-9]{64}", expected or ""):
        raise ValueError("JPMORGAN_TERMS_CONFIRMATION_MISSING_OR_CHANGED")


def same_origin(url: str) -> bool:
    try:
        value = urlsplit(url)
        return (
            value.scheme == "https"
            and value.hostname == "www.jpmorgan-zertifikate.de"
            and (value.port in {None, 443} and not value.username and not value.password)
        )
    except ValueError:
        return False


async def inspect_terms(page: Page) -> tuple[str, str]:
    denied = await page.evaluate(ACCESS_STATE)
    if denied == "ISSUER_RENDER_ACCESS_BLOCKED":
        raise ValueError(denied)
    # Non-binding privacy choice only. Never use the broad word "accept" here.
    reject = page.get_by_role("button", name="Alle ablehnen", exact=True)
    attempts: list[str] = []
    # At most two clicks, with a third read pass if the overlay arrived late.
    for _ in range(3):
        if await reject.count() == 1 and await reject.is_visible():
            if len(attempts) >= 2:
                break
            await reject.click(timeout=3000)
            try:
                await reject.wait_for(state="hidden", timeout=COOKIE_DISMISS_TIMEOUT_MS)
            except BrowserTimeout:
                attempts.append("STILL_VISIBLE_AFTER_WAIT")
                continue
            attempts.append("HIDDEN_AFTER_WAIT")
        text = await page.locator("body").inner_text(timeout=5000)
        # The cookie overlay can arrive after the first visibility check. Dismiss
        # it before returning so it cannot cover the eventual consent control.
        if await reject.count() != 1 or not await reject.is_visible():
            return terms_digest(text)
    raise CookieBannerNotDismissed(attempts)


async def _setup(
    *,
    confirm: str | None,
    accepted: bool,
    isin: str = ISIN,
    eligibility_confirmed: bool = False,
    remember: bool = False,
) -> dict[str, object]:
    if accepted and not eligibility_confirmed:
        raise ValueError("JPMORGAN_EXPLICIT_ELIGIBILITY_CONFIRMATION_REQUIRED")
    if accepted and STATE_PATH.is_symlink():
        raise ConsentStateNotStored(
            "ISSUER_CONSENT_DESTINATION_SYMLINK", {"before_browser_start": True}
        )
    existing: StorageState | None = None
    if accepted:
        with traced_step("CHECK_EXISTING_STATE"):
            existing = load_consent(STATE_PATH)
            if existing is not None:
                record = json.loads(STATE_PATH.read_text())
                require_confirmation(record["terms_sha256"], confirm, accepted)
    renderer = IssuerRenderer()
    stage = "BROWSER_START"
    blocked_requests: dict[str, int] = {}
    try:
        async with asyncio.timeout(SETUP_TIMEOUT_SECONDS):
            with traced_step("BROWSER_START"):
                await renderer.start()
            assert renderer.browser is not None
            url = product_url("JPMORGAN", isin)
            if existing is not None:
                with traced_step("VERIFY_EXISTING_STATE_IN_FRESH_CONTEXT"):
                    await renderer._capture("JPMORGAN", isin, url, consent_override=existing)
                return {
                    "schema_version": "JPMORGAN_CONSENT_SETUP_V3",
                    "status": "EXISTING_CONSENT_REUSE_VERIFIED",
                    "accepted": True,
                    "new_acceptance_performed": False,
                    "product_reuse_verified": True,
                    "terms_sha256": confirm,
                    "isin": isin,
                    "mapping_created": False,
                    "checked_at": datetime.now(UTC).isoformat(),
                }
            with traced_step("CREATE_ACCEPTANCE_CONTEXT"):
                context = await renderer.browser.new_context(
                    accept_downloads=False, service_workers="block", ignore_https_errors=False
                )
            context_closed = False
            try:
                with traced_step("CREATE_ACCEPTANCE_PAGE"):
                    page = await context.new_page()
                approved = False
                requests = 0
                form_action: str | None = None
                blocked = False

                async def guard(route: Route) -> None:
                    nonlocal requests, blocked
                    request = route.request
                    requests += 1
                    allowed = requests <= 128 and allowed_resource(request.url, "JPMORGAN")
                    if request.is_navigation_request():
                        allowed = (
                            allowed
                            and request.frame == page.main_frame
                            and (
                                allowed_product_url(request.url, "JPMORGAN", isin)
                                or (approved and same_origin(request.url))
                            )
                        )
                    if request.method not in {"GET", "HEAD"}:
                        allowed = (
                            allowed
                            and approved
                            and request.method == "POST"
                            and (form_action is not None and request.url == form_action)
                        )
                    if allowed:
                        await route.continue_()
                    else:
                        # Aggregate host/method/type only; omit paths, query
                        # strings, request bodies, headers and session data.
                        host = urlsplit(request.url).hostname or "NO_HOST"
                        key = f"{host}|{request.method}|{request.resource_type}"
                        if key not in blocked_requests and len(blocked_requests) >= 16:
                            key = "OTHER_BLOCKED_REQUESTS"
                        blocked_requests[key] = blocked_requests.get(key, 0) + 1
                        if request.is_navigation_request():
                            blocked = True
                        await route.abort()

                async def close_socket(socket: WebSocketRoute) -> None:
                    await socket.close()

                with traced_step("INSTALL_REQUEST_GUARDS"):
                    await context.route("**/*", guard)
                    await context.route_web_socket("**/*", close_socket)
                with traced_step("LOAD_TERMS_PAGE"):
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                if response is None or response.status != 200:
                    raise ValueError("JPMORGAN_TERMS_PAGE_UNAVAILABLE")
                stage = "INITIAL_PAGE"
                with traced_step("INSPECT_INITIAL_TERMS_AND_COOKIE_BANNER"):
                    text, digest = await inspect_terms(page)
                with traced_step("INSPECT_INITIAL_FORM"):
                    form = await inspect_form(page)
                control = page.locator(SUBMIT_SELECTOR)
                result: dict[str, object] = {
                    "schema_version": "JPMORGAN_CONSENT_SETUP_V3",
                    "source_url": url,
                    "terms_sha256": digest,
                    "terms_text": text,
                    "accept_control_count": form["accept_control_count"],
                    "form": form,
                    "form_snapshot_basis": "BEFORE_OPERATOR_ACTIONS",
                    "eligibility_confirmation_required": True,
                    "accepted": False,
                    "status": "REVIEW_REQUIRED",
                    "checked_at": datetime.now(UTC).isoformat(),
                }
                if not accepted:
                    return result
                require_confirmation(digest, confirm, accepted)
                with traced_step("INSPECT_SUBMIT_ACTION"):
                    action = await control.evaluate(
                        "e => e.form ? {action:e.form.action, method:e.form.method} : null"
                    )
                if isinstance(action, dict) and action.get("method", "").lower() == "post":
                    candidate = action.get("action")
                    if not isinstance(candidate, str) or not same_origin(candidate):
                        raise ValueError("JPMORGAN_ACCEPT_ACTION_UNTRUSTED")
                    form_action = candidate
                # All declarations require the explicit operator flag and a current hash.
                stage = "BEFORE_DECLARATIONS"
                with traced_step("RECHECK_TERMS_BEFORE_DECLARATIONS"):
                    _, current = await inspect_terms(page)
                require_confirmation(current, confirm, accepted)
                approved = True
                with traced_step("APPLY_CONFIRMED_DECLARATIONS"):
                    await apply_choices(
                        page,
                        accepted=accepted,
                        eligibility_confirmed=eligibility_confirmed,
                        remember=remember,
                    )
                with traced_step("WAIT_FOR_ACCEPT_CONTROL"):
                    await control.wait_for(state="visible", timeout=5000)
                with traced_step("INSPECT_COMPLETED_FORM"):
                    await inspect_form(page)
                stage = "AFTER_DECLARATIONS_BEFORE_SUBMIT"
                with traced_step("RECHECK_TERMS_BEFORE_SUBMIT"):
                    _, current = await inspect_terms(page)
                require_confirmation(current, confirm, accepted)
                with traced_step("SUBMIT_CONFIRMED_TERMS"):
                    await control.click(timeout=5000)
                with traced_step("LOAD_PRODUCT_AFTER_SUBMIT"):
                    await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
                if blocked:
                    raise ValueError("JPMORGAN_SETUP_NAVIGATION_BLOCKED")
                with traced_step("VERIFY_PRODUCT_AFTER_SUBMIT"):
                    deadline = asyncio.get_running_loop().time() + 8
                    while True:
                        raw = (await page.evaluate(SANITIZED_DOM)).encode()
                        try:
                            parse_product_page(raw, "JPMORGAN", isin, page.url)
                            break
                        except ValueError:
                            if asyncio.get_running_loop().time() >= deadline:
                                raise ValueError(
                                    "JPMORGAN_CONSENT_NOT_VERIFIED_NO_STATE_SAVED"
                                ) from None
                            await asyncio.sleep(0.25)
                with traced_step("READ_SCOPED_BROWSER_STATE"):
                    state = restrict_state(await context.storage_state())
                if not state["cookies"] and not state["origins"]:
                    raise ValueError("JPMORGAN_REUSABLE_CONSENT_STATE_MISSING")
                with traced_step("CLOSE_ACCEPTANCE_CONTEXT"):
                    await asyncio.wait_for(context.close(), timeout=3)
                context_closed = True
                storage_result = await verify_and_save_consent(renderer, state, digest, isin, url)
                return {key: value for key, value in result.items() if key != "terms_text"} | {
                    "accepted": True,
                    "new_acceptance_performed": True,
                    "product_reuse_verified": True,
                    "status": "CONSENT_STORED_PRODUCT_VERIFIED",
                    "mapping_created": False,
                    "eligibility_confirmed_by_operator": True,
                    "remember_30_days_selected": remember,
                    **storage_result,
                }
            finally:
                if not context_closed:
                    primary_error = sys.exc_info()[1]
                    try:
                        with traced_step("CLEANUP_ACCEPTANCE_CONTEXT"):
                            await asyncio.wait_for(context.close(), timeout=3)
                    except Exception:
                        if primary_error is None:
                            raise
    except CookieBannerNotDismissed as exc:
        exc.diagnostics["stage"] = stage
        exc.diagnostics["blocked_request_counts"] = blocked_requests
        raise
    finally:
        primary_error = sys.exc_info()[1]
        try:
            with traced_step("CLEANUP_RENDERER"):
                await asyncio.wait_for(renderer.close(), timeout=5)
        except Exception:
            if primary_error is None:
                raise


async def setup(
    *,
    confirm: str | None,
    accepted: bool,
    isin: str = ISIN,
    eligibility_confirmed: bool = False,
    remember: bool = False,
    trace: SetupTrace | None = None,
) -> dict[str, object]:
    trace = trace if trace is not None else SetupTrace()
    token = CURRENT_TRACE.set(trace)
    trace.before = stored_state_metadata(confirm)
    try:
        result = await _setup(
            confirm=confirm,
            accepted=accepted,
            isin=isin,
            eligibility_confirmed=eligibility_confirmed,
            remember=remember,
        )
    except Exception as exc:
        trace.error_chain = error_details(exc)
        raise
    finally:
        trace.after = stored_state_metadata(confirm)
        CURRENT_TRACE.reset(token)
    result["setup_diagnostics"] = trace.report()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept-current-jpmorgan-terms", action="store_true")
    parser.add_argument("--confirm-sha256")
    parser.add_argument("--confirm-de-at-residence-and-non-us-person", action="store_true")
    parser.add_argument("--remember-30-days", action="store_true")
    parser.add_argument("--isin", default=ISIN)
    args = parser.parse_args()
    if bool(args.confirm_sha256) != args.accept_current_jpmorgan_terms:
        parser.error("Acceptance requires both explicit flag and reviewed terms SHA-256")
    if args.accept_current_jpmorgan_terms and not args.confirm_de_at_residence_and_non_us_person:
        parser.error("Acceptance additionally requires --confirm-de-at-residence-and-non-us-person")
    if not args.accept_current_jpmorgan_terms and (
        args.confirm_de_at_residence_and_non_us_person or args.remember_30_days
    ):
        parser.error("Declaration and remember flags are only valid with explicit acceptance")
    trace = SetupTrace()
    try:
        with (STATE_PATH.parent / "jpmorgan-setup.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = asyncio.run(
                setup(
                    confirm=args.confirm_sha256,
                    accepted=args.accept_current_jpmorgan_terms,
                    isin=args.isin,
                    eligibility_confirmed=args.confirm_de_at_residence_and_non_us_person,
                    remember=args.remember_30_days,
                    trace=trace,
                )
            )
    except Exception as exc:
        reason = (
            str(exc) if re.fullmatch(r"[A-Z][A-Z0-9_]{1,100}", str(exc)) else type(exc).__name__
        )
        failure: dict[str, object] = {
            "status": "SETUP_NOT_COMPLETED",
            "reason": reason,
            "setup_diagnostics": trace.report(),
            "error_chain": error_details(exc),
        }
        if isinstance(exc, (CookieBannerNotDismissed, ConsentStateNotStored)):
            failure["diagnostics"] = exc.diagnostics
        print(json.dumps(failure))
        raise SystemExit(2) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

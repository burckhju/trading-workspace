"""Local, operator-created JPMorgan consent state; never copied from another browser."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from playwright.async_api import StorageState

STATE_PATH = Path("/state/jpmorgan-consent.json")
DOMAINS = {"jpmorgan-zertifikate.de", "www.jpmorgan-zertifikate.de"}
ORIGINS = {"https://" + host for host in DOMAINS}


def restrict_state(state: StorageState) -> StorageState:
    return {
        "cookies": [c for c in state.get("cookies", []) if c["domain"].lstrip(".") in DOMAINS],
        "origins": [o for o in state.get("origins", []) if o["origin"] in ORIGINS],
    }


def load_consent(path: Path = STATE_PATH) -> StorageState | None:
    if not path.exists():
        return None
    try:
        if path.is_symlink() or path.stat().st_size > 262_144:
            raise ValueError
        record = json.loads(path.read_text())
        if record.get("schema") != "JPMORGAN_OPERATOR_CONSENT_V1" or not re.fullmatch(
            r"[a-f0-9]{64}", record.get("terms_sha256", "")
        ):
            raise ValueError
        accepted = datetime.fromisoformat(record["accepted_at"])
        if accepted.utcoffset() is None or accepted > datetime.now(UTC):
            raise ValueError
        state = record["storage_state"]
        if not isinstance(state, dict) or set(state) != {"cookies", "origins"}:
            raise ValueError
        if not isinstance(state["cookies"], list) or not isinstance(state["origins"], list):
            raise ValueError
        typed = cast(StorageState, state)
        if restrict_state(typed) != state:
            raise ValueError
        return typed
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("ISSUER_CONSENT_STATE_INVALID") from None


def save_consent(state: StorageState, terms_sha256: str, path: Path = STATE_PATH) -> None:
    if not re.fullmatch(r"[a-f0-9]{64}", terms_sha256):
        raise ValueError("ISSUER_CONSENT_HASH_INVALID")
    if path.is_symlink():
        raise ValueError("ISSUER_CONSENT_STATE_INVALID")
    record = {
        "schema": "JPMORGAN_OPERATOR_CONSENT_V1",
        "terms_sha256": terms_sha256,
        "accepted_at": datetime.now(UTC).isoformat(),
        "storage_state": restrict_state(state),
    }
    data = json.dumps(record).encode()
    if len(data) > 262_144:
        raise ValueError("ISSUER_CONSENT_STATE_INVALID")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def consent_status() -> str:
    try:
        return "STORED" if load_consent() is not None else "NOT_CONFIGURED"
    except ValueError:
        return "INVALID"

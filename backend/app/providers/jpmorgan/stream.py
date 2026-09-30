"""Bounded anonymous snapshot batches; strict merge decoding without JavaScript eval."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

from websockets.asyncio.client import ClientConnection
from websockets.typing import Origin, Subprotocol

from app.providers.jpmorgan.products import INSTRUMENTS

URL = "wss://push-jpmorgan-zertifikate.smarthouse.de/lightstreamer"
SCHEMA = ("bid", "bidsize", "ask", "asksize", "quotetime")
START = re.compile(r"\bstart\('([A-Za-z0-9_-]{1,128})'\s*,")
ERROR = re.compile(r"\berror\(\s*(-?[0-9]+)\s*,")
CALLBACK = re.compile(r"\b([zd])\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,([^;\r\n]{0,2000})\)\s*;")
TOKEN = re.compile(r"\s*(?:'([^'\\\r\n]{0,128})'|([1-9][0-9]{0,2}))\s*(,|$)")


@dataclass(frozen=True)
class StreamItem:
    fields: dict[str, str | None]
    received_at: datetime


def decode_fields(
    raw: str, previous: dict[str, str | None] | None = None
) -> tuple[dict[str, str | None], list[str]]:
    """Merge unchanged runs against this item's state; never eval received JS."""
    values: list[str | None] = (
        [None] * len(SCHEMA) if previous is None else [previous[k] for k in SCHEMA]
    )
    supplied = []
    column = offset = 0
    while offset < len(raw):
        match = TOKEN.match(raw, offset)
        if match is None:
            raise ValueError("UNSUPPORTED_FIELD_VALUE")
        if match[2] is not None:
            if previous is None:
                raise ValueError("UNCHANGED_WITHOUT_SNAPSHOT")
            column += int(match[2])
        else:
            value: str | None = match[1]
            if value is None:
                raise ValueError("UNSUPPORTED_FIELD_VALUE")
            if any(ord(c) < 32 or ord(c) > 126 for c in value):
                raise ValueError("UNSUPPORTED_FIELD_VALUE")
            if value == "#":
                value = None
            elif value == "$":
                value = ""
            elif value.startswith(("#", "$")):
                value = value[1:]
            if column >= len(SCHEMA):
                raise ValueError("FIELD_COUNT_MISMATCH")
            values[column] = value
            supplied.append(SCHEMA[column])
            column += 1
        if column > len(SCHEMA) or (match[3] == "," and match.end() == len(raw)):
            raise ValueError("FIELD_COUNT_MISMATCH")
        offset = match.end()
    if column != len(SCHEMA):
        raise ValueError("FIELD_COUNT_MISMATCH")
    return dict(zip(SCHEMA, values, strict=True)), supplied


async def fetch_batch(
    timeout_seconds: float = 40,
    *,
    connector: Callable[..., AbstractAsyncContextManager[ClientConnection]] | None = None,
    instruments: dict[str, str] | None = None,
) -> dict[str, StreamItem]:
    """One session for the seven exact products. Partial timeout keeps received items.

    A protocol/transport failure discards the batch; only the bounded deadline may
    finish with missing products. Every batch starts from empty per-item state.
    """
    if connector is None:
        from websockets import connect

        connector = connect
    instruments = dict(INSTRUMENTS if instruments is None else instruments)
    if not 1 <= len(instruments) <= 64 or len(set(instruments.values())) != len(instruments):
        raise ValueError("JPMORGAN_INVALID_BINDINGS")
    for isin, stream_id in instruments.items():
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin) or not re.fullmatch(
            r"X[A-Z0-9]{1,20}" + re.escape(isin), stream_id
        ):
            raise ValueError("JPMORGAN_INVALID_BINDINGS")
    isins = tuple(instruments)
    items: dict[str, StreamItem] = {}
    session = None
    received_bytes = 0
    try:
        async with connector(
            URL,
            subprotocols=[Subprotocol("js.lightstreamer.com")],
            origin=Origin("https://www.jpmorgan-zertifikate.de"),
            open_timeout=min(10, timeout_seconds),
            close_timeout=2,
            ping_interval=None,
            max_size=200_000,
        ) as socket:
            try:
                async with asyncio.timeout(timeout_seconds):
                    await socket.send(
                        "create_session\r\n"
                        + urlencode(
                            {
                                "LS_op2": "create",
                                "LS_phase": "1",
                                "LS_cause": "new.api",
                                "LS_keepalive_millis": "5000",
                                "LS_cid": "pcYgxn8m8 feOojyA1T661j3g2.pz479h7m",
                                "LS_adapter_set": "SmarthouseFeed",
                                "LS_user": "",
                                "LS_container": "lsc",
                            }
                        )
                    )
                    for _ in range(1000):
                        frame = await socket.recv()
                        received_at = datetime.now(UTC)
                        if not isinstance(frame, str):
                            raise ValueError("JPMORGAN_BINARY_FRAME")
                        received_bytes += len(frame.encode())
                        if received_bytes > 1_000_000:
                            raise ValueError("JPMORGAN_BATCH_LIMIT")
                        starts = list(START.finditer(frame))
                        if len(starts) > 1 or (starts and session is not None):
                            raise ValueError("JPMORGAN_SESSION_RESTART")
                        if starts:
                            session = starts[0][1]
                        if ERROR.search(frame):
                            raise ValueError("JPMORGAN_SERVER_REJECTED")
                        if re.search(
                            r"\b(?:end|retry|loop)\(\s*(?:'[^'\r\n]*'|[0-9]+)?\s*\)\s*;", frame
                        ):
                            raise ValueError("JPMORGAN_RECONNECT_REQUIRED")
                        if re.search(r"\b[nrp]\(\s*[0-9]+\s*,", frame):
                            raise ValueError("JPMORGAN_UNSUPPORTED_CALLBACK")
                        if starts:
                            await socket.send(
                                "control\r\n"
                                + urlencode(
                                    {
                                        "LS_mode": "MERGE",
                                        "LS_id": " ".join(instruments.values()),
                                        "LS_schema": " ".join(SCHEMA),
                                        "LS_data_adapter": "MDS5",
                                        "LS_snapshot": "true",
                                        "LS_table": "1",
                                        "LS_req_phase": "1",
                                        "LS_win_phase": "1",
                                        "LS_op": "add",
                                        "LS_session": session,
                                    }
                                )
                            )
                        callbacks = list(CALLBACK.finditer(frame))
                        if len(re.findall(r"\b[zd]\(\s*[0-9]+\s*,", frame)) != len(callbacks):
                            raise ValueError("JPMORGAN_UNPARSED_CALLBACK")
                        for call in callbacks:
                            kind, table, index = call[1], int(call[2]), int(call[3])
                            if session is None or table != 1 or not 1 <= index <= len(isins):
                                raise ValueError("JPMORGAN_UNSUBSCRIBED_ITEM")
                            isin = isins[index - 1]
                            previous = items.get(isin)
                            if (kind == "z" and previous) or (kind == "d" and not previous):
                                raise ValueError("JPMORGAN_SNAPSHOT_SEQUENCE")
                            fields, _ = decode_fields(
                                call[4], previous.fields if previous else None
                            )
                            items[isin] = StreamItem(fields, received_at)
                        if len(items) == len(isins):
                            break
                    else:
                        raise ValueError("JPMORGAN_FRAME_LIMIT")
            except TimeoutError:
                if not items:
                    raise ValueError("JPMORGAN_SNAPSHOT_TIMEOUT") from None
            finally:
                if session is not None:
                    await asyncio.wait_for(
                        socket.send(
                            "control\r\n"
                            + urlencode(
                                {
                                    "LS_op": "destroy",
                                    "LS_session": session,
                                }
                            )
                        ),
                        2,
                    )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Never include session IDs, server bodies or credentials in diagnostics.
        code = str(exc)
        if not re.fullmatch(r"JPMORGAN_[A-Z_]{1,70}", code):
            code = "JPMORGAN_STREAM_FAILURE"
        raise ValueError(code) from None
    return items

"""Read the running backend's valuation port for an operator's one-off cycle."""

from uuid import UUID

import httpx

from app.features.position_monitoring.api.dtos import ProductPositionValuationResponse
from app.features.position_monitoring.service.product_valuation import ProductPositionValuation
from app.features.position_monitoring.service.quote_sources import QuoteSourceAttempt


def backend_origin(value: str) -> str:
    """Accept an explicit HTTP origin, without credentials or ambiguous URL parts."""
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL:
        raise ValueError("Backend URL must be an HTTP(S) origin") from None
    if (
        url.scheme not in {"http", "https"}
        or not url.host
        or url.userinfo
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
    ):
        raise ValueError("Backend URL must be an HTTP(S) origin without credentials or a path")
    return str(url).rstrip("/")


class BackendProductValuations:
    """GET existing valuations; all trading-state writes remain in the normal cycle."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        diagnostics: list[dict[str, object]] | None = None,
    ) -> None:
        self._client = client
        self._diagnostics = diagnostics

    async def check_ready(self) -> None:
        try:
            response = await self._client.get("/health/ready")
            payload = response.json() if response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            raise RuntimeError("BACKEND_NOT_READY") from None
        if not isinstance(payload, dict) or payload.get("status") != "ready":
            raise RuntimeError("BACKEND_NOT_READY")

    async def for_trade(self, trade_id: UUID) -> ProductPositionValuation | None:
        try:
            response = await self._client.get(
                f"/api/v1/position-monitoring/trades/{trade_id}/product-valuation"
            )
        except httpx.HTTPError:
            self._failure(trade_id, "BACKEND_TRANSPORT_ERROR")
            raise RuntimeError("BACKEND_TRANSPORT_ERROR") from None
        if response.status_code == 404:
            self._failure(trade_id, "BACKEND_OPEN_POSITION_NOT_FOUND")
            return None
        if response.status_code != 200:
            reason = f"BACKEND_HTTP_{response.status_code}"
            self._failure(trade_id, reason)
            raise RuntimeError(reason)
        try:
            value = ProductPositionValuationResponse.model_validate_json(response.content)
        except ValueError:
            self._failure(trade_id, "BACKEND_VALUATION_SCHEMA_INVALID")
            raise RuntimeError("BACKEND_VALUATION_SCHEMA_INVALID") from None
        if value.trade_id != trade_id:
            self._failure(trade_id, "BACKEND_TRADE_IDENTITY_MISMATCH")
            raise RuntimeError("BACKEND_TRADE_IDENTITY_MISMATCH")
        if self._diagnostics is not None:
            self._diagnostics.append(
                value.model_dump(
                    mode="json",
                    include={"trade_id", "status", "reason", "selected_source", "source_attempts"},
                )
            )
        return ProductPositionValuation(
            **value.model_dump(exclude={"source_attempts"}),
            source_attempts=tuple(
                QuoteSourceAttempt(**a.model_dump()) for a in value.source_attempts
            ),
        )

    def _failure(self, trade_id: UUID, reason: str) -> None:
        if self._diagnostics is not None:
            self._diagnostics.append(
                {"trade_id": str(trade_id), "status": "ERROR", "reason": reason}
            )

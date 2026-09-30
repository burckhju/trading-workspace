"""Private Docker-only renderer API. Only provider + valid ISIN are accepted."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from app.features.market.contracts import is_canonical_isin
from app.providers.issuer_renderer.browser import VERSION, IssuerRenderer, RenderFailure
from app.providers.issuer_renderer.consent_state import consent_status

renderer = IssuerRenderer()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await renderer.start()
    try:
        yield
    finally:
        await renderer.close()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider: Literal["JPMORGAN", "MORGAN_STANLEY"]
    isin: str

    @field_validator("isin")
    @classmethod
    def valid_isin(cls, value: str) -> str:
        if not is_canonical_isin(value):
            raise ValueError("ISSUER_ISIN_INVALID")
        return value


@app.get("/health")
async def health() -> JSONResponse:
    ready = renderer.healthy()
    return JSONResponse(
        {
            "ready": ready,
            "version": VERSION,
            "chromium_sandbox": True,
            "renderer_revision": "1.4.0",
            "jpmorgan_consent": consent_status(),
        },
        status_code=200 if ready else 503,
    )


@app.post("/render")
async def render(request: RenderRequest) -> JSONResponse:
    try:
        return JSONResponse(await renderer.render(request.provider, request.isin))
    except RenderFailure as exc:
        reason = str(exc)
        return JSONResponse({"reason": reason}, status_code=503)

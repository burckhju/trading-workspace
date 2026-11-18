"""Original-document readiness outside the economic evaluation transaction."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import select

from app.database import DatabaseManager
from app.features.market.persistence.models import IssuerModel
from app.features.market_data.service.review_calendars import (
    acquire_nyse_calendar,
    acquire_xstu_day_calendar,
)
from app.features.product.persistence.models import WarrantModel
from app.features.product.persistence.review_evidence import (
    ProductReviewAcquisitionModel,
)
from app.features.product.service.price_scale_evidence import require_warrant
from app.features.product.service.review_evidence import record_original_kid
from app.features.trade_position.service.open_position_reader import OpenPositionReader
from app.providers.product_review_documents import fetch_original, kid_url

logger = logging.getLogger(__name__)


class ProductReviewReadiness:
    """Bounded public document reads; never enable or select a quote provider.

    V2 composition owns the activation. An original is reused until the next daily
    source check. Failed acquisition retries hourly; caller still evaluates all
    retained facts and shows missing coverage. Passive API readers never call us.
    """

    def __init__(self, database: DatabaseManager) -> None:
        self._database = database
        self._lock = asyncio.Lock()

    async def prepare_for_review(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        position_id: UUID,
    ) -> None:
        async with self._lock:
            await self._prepare(
                workspace_id=workspace_id, trade_id=trade_id, position_id=position_id
            )

    async def _prepare(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        position_id: UUID,
    ) -> None:
        now = datetime.now(UTC)
        async with self._database.session_context() as session:
            position = await OpenPositionReader(session).read(
                workspace_id=workspace_id, trade_id=trade_id
            )
            if position is None or position.position_id != position_id:
                return
            warrant_id = position.warrant_id
            await require_warrant(
                session, workspace_id=workspace_id, warrant_id=warrant_id, lock=True
            )
            attempt = await session.get(ProductReviewAcquisitionModel, (workspace_id, warrant_id))
            if attempt is not None and attempt.next_attempt_at > now:
                return
            row = (
                await session.execute(
                    select(WarrantModel, IssuerModel)
                    .join(
                        IssuerModel,
                        IssuerModel.id == WarrantModel.issuer_id,
                    )
                    .where(WarrantModel.id == warrant_id)
                )
            ).one()
            warrant, issuer = row
            url = kid_url(issuer.legal_name, warrant.isin)
            if attempt is None:
                attempt = ProductReviewAcquisitionModel(
                    workspace_id=workspace_id, warrant_id=warrant_id
                )
                session.add(attempt)
            attempt.attempted_at = now
            attempt.next_attempt_at = now + timedelta(hours=1)
            attempt.outcome = "STARTED" if url else "PRODUCT_DOCUMENT_PROVIDER_UNSUPPORTED"
            await session.commit()
        outcome = "AVAILABLE" if url else "PRODUCT_DOCUMENT_PROVIDER_UNSUPPORTED"
        async with httpx.AsyncClient(
            timeout=15.0, headers={"User-Agent": "trading-workspace-document-review/1"}
        ) as client:
            if url is not None:
                try:
                    document = await fetch_original(client, url)
                    retrieved_at = datetime.now(UTC)
                    async with self._database.session_context() as session:
                        await record_original_kid(
                            session,
                            workspace_id=workspace_id,
                            warrant_id=warrant_id,
                            source_reference=url,
                            document=document,
                            retrieved_at=retrieved_at,
                            now=datetime.now(UTC),
                        )
                        await session.commit()
                except Exception:
                    outcome = "PRODUCT_DOCUMENT_ACQUISITION_FAILED"
                    logger.exception(
                        "product_review_document_acquisition_failed",
                        extra={"warrant_id": str(warrant_id)},
                    )
            # Independent originals are not suppressed by a failed product or calendar fetch.
            for acquire in (acquire_nyse_calendar, acquire_xstu_day_calendar):
                try:
                    async with self._database.session_context() as session:
                        await acquire(
                            session,
                            client,
                            workspace_id=workspace_id,
                            now=datetime.now(UTC),
                        )
                        await session.commit()
                except Exception:
                    outcome = "REVIEW_READINESS_PARTIAL"
                    logger.exception(
                        "review_calendar_acquisition_failed",
                        extra={"source": acquire.__name__},
                    )
        async with self._database.session_context() as session:
            attempt = await session.get(ProductReviewAcquisitionModel, (workspace_id, warrant_id))
            if attempt is not None and attempt.attempted_at == now:
                attempt.outcome = outcome
                attempt.next_attempt_at = datetime.now(UTC) + timedelta(
                    hours=24 if outcome == "AVAILABLE" else 1
                )
                await session.commit()

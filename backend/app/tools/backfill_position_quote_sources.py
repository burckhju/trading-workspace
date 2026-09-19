"""Preview or atomically backfill quote-source decisions for open positions."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.di import ApplicationContainer
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.domain.position_quote_source import (
    PositionQuoteSourceDecision,
    PositionQuoteSourceSelectionStatus,
)
from app.features.market_data.persistence.models import PositionQuoteSourceSelectionModel
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.position_quote_source import (
    PositionQuoteSourceSelector,
    choose_position_quote_source,
)
from app.features.market_data.service.provider_policy import allowed_warrant_quote_providers
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.product_selection.persistence.models import ProductEvaluationModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def _candidate_payload(candidate) -> dict[str, object]:
    return {
        "provider": candidate.provider.value,
        "listing_id": str(candidate.listing_id),
        "mapping_id": str(candidate.mapping_id) if candidate.mapping_id is not None else None,
        "mapping_version": candidate.mapping_version,
        "identity_key": candidate.identity_key,
        "currency": candidate.currency,
        "mic": candidate.mic,
        "provider_exchange_code": candidate.provider_exchange_code,
    }


def _selection_payload(selection: PositionQuoteSourceSelectionModel) -> dict[str, object]:
    return {
        "status": selection.selection_status,
        "reason": selection.selection_reason,
        "provider": selection.provider,
        "listing_id": str(selection.warrant_listing_id) if selection.warrant_listing_id else None,
        "mapping_id": (
            str(selection.warrant_provider_mapping_id)
            if selection.warrant_provider_mapping_id
            else None
        ),
        "mapping_version": selection.mapping_version,
        "identity_key": selection.identity_key,
    }


def _decision_payload(decision: PositionQuoteSourceDecision) -> dict[str, object]:
    selected = decision.selected
    return {
        "status": decision.status.value,
        "reason": decision.reason,
        "provider": selected.provider.value if selected else None,
        "listing_id": str(selected.listing_id) if selected else None,
        "mapping_id": str(selected.mapping_id) if selected and selected.mapping_id else None,
        "mapping_version": selected.mapping_version if selected else None,
        "identity_key": selected.identity_key if selected else None,
    }


def _preview_hash(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

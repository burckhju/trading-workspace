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

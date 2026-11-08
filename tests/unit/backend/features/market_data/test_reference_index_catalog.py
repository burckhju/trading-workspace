"""Direct index identity must come from the catalog before validation or price writes.

The real reference service, identity resolver, HTTP client and resilience components
run here. Only persistence I/O and the external HTTP transport are replaced.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from random import Random
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import EodhdSettings
from app.features.market.persistence.top_down_models import MarketReferenceModel
from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    PriceType,
)
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)
from app.features.market_data.service.errors import (
    MarketDataAuthorizationError,
    MarketDataBudgetExhaustedError,
    MarketDataUnavailableError,
)
from app.features.market_data.service.reference_market_data import ReferenceMarketDataService
from app.providers.eodhd.client import EodhdClient
from app.providers.shared.budget import DailyCallBudget
from app.providers.shared.rate_limit import TokenBucketRateLimiter
from app.providers.shared.retry import RetryPolicy

WORKSPACE = UUID("00000000-0000-4000-8000-000000000001")
REFERENCE = UUID("00000000-0000-4000-8000-000000000002")
INSTRUMENT = UUID("00000000-0000-4000-8000-000000000003")
MAPPING = UUID("00000000-0000-4000-8000-000000000004")
START = date(2026, 11, 2)
END = date(2026, 11, 6)
CATALOG_PATH = "/api/exchange-symbol-list/INDX"

# Observed public search identities: neither is the requested GSPC.INDX index.
SEARCH_OTHER_INSTRUMENTS = [
    {
        "Code": "GSPCX",
        "Exchange": "US",
        "Name": "GOLDMAN SACHS CAPITAL GROWTH FUND CLASS C",
        "Type": "FUND",
        "Currency": "USD",
    },
    {
        "Code": "GSPCROP",
        "Exchange": "NSE",
        "Name": "GSP Crop Science Limited",
        "Type": "Common Stock",
        "Currency": "INR",
    },
]

# Synthetic provider fixture, encoded as numeric JSON to exercise Decimal decoding.
DAILY_PRICES = b"""[
  {"date":"2026-11-02","open":100.125,"high":102.25,"low":99.5,
   "close":101.875,"adjusted_close":null,"volume":null},
  {"date":"2026-11-06","open":101.75,"high":103.125,"low":100.5,
   "close":102.625,"adjusted_close":102.625,"volume":0},
  {"date":"2026-11-09","open":104,"high":105,"low":103,
   "close":104.25,"adjusted_close":104.25,"volume":200}
]"""


def index_row(**changes: object) -> dict[str, object]:
    return {
        "Code": "GSPC",
        "Exchange": "INDX",
        "Name": "S&P 500 Index",
        "Type": "INDEX",
        "Currency": "USD",
        **changes,
    }


class TestClock:
    __test__ = False

    def __init__(self) -> None:
        self.now = datetime(2026, 11, 8, 12, tzinfo=UTC)
        self.mono = 0.0
        self.sleeps: list[float] = []

    def utcnow(self) -> datetime:
        return self.now

    def monotonic(self) -> float:
        return self.mono

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.mono += seconds


@dataclass
class Provider:
    catalog: object
    search: object = field(default_factory=lambda: SEARCH_OTHER_INSTRUMENTS)
    catalog_statuses: list[int] = field(default_factory=list)
    requests: list[httpx.Request] = field(default_factory=list)

    def respond(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == CATALOG_PATH:
            status = self.catalog_statuses.pop(0) if self.catalog_statuses else 200
            return httpx.Response(status, json=self.catalog)
        if path.startswith("/api/search/"):
            return httpx.Response(200, json=self.search)
        if path.startswith("/api/eod/"):
            return httpx.Response(
                200, content=DAILY_PRICES, headers={"Content-Type": "application/json"}
            )
        raise AssertionError(f"Unexpected provider path: {path}")

    @property
    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]


@dataclass
class Runtime:
    service: ReferenceMarketDataService
    mapping: ProviderInstrumentMappingModel
    session: Mock
    provider: Provider
    budget: DailyCallBudget
    clock: TestClock

    async def validate(self) -> ProviderInstrumentMappingModel:
        return await self.service.validate_mapping(
            workspace_id=WORKSPACE, market_reference_id=REFERENCE
        )

    async def import_prices(self):
        return await self.service.import_daily_prices(
            workspace_id=WORKSPACE,
            market_reference_id=REFERENCE,
            start_date=START,
            end_date=END,
        )

    @property
    def added(self) -> list[object]:
        return [call.args[0] for call in self.session.add.call_args_list]


@asynccontextmanager
async def runtime(
    catalog: object,
    *,
    symbol: str = "GSPC",
    exchange: str = "INDX",
    status: MappingStatus = MappingStatus.DISABLED,
    budget_limit: int = 100,
) -> AsyncIterator[Runtime]:
    clock = TestClock()
    mapping = ProviderInstrumentMappingModel(
        id=MAPPING,
        workspace_id=WORKSPACE,
        listing_id=None,
        market_data_instrument_id=INSTRUMENT,
        provider=MarketDataProvider.EODHD,
        provider_symbol=symbol,
        provider_exchange_code=exchange,
        status=status,
        validated_at=None,
        validation_message="Awaiting explicit validation",
        created_at=clock.utcnow(),
        updated_at=clock.utcnow(),
        version=1,
    )
    instrument = MarketDataInstrumentModel(
        id=INSTRUMENT,
        workspace_id=WORKSPACE,
        kind="MARKET_REFERENCE",
        listing_id=None,
        market_reference_id=REFERENCE,
        created_at=clock.utcnow(),
    )

    def scalar(statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is MarketReferenceModel:
            return True
        if entity is MarketDataInstrumentModel:
            return instrument
        if entity is ProviderInstrumentMappingModel:
            return mapping
        if entity is DailyPriceModel:
            return None
        raise AssertionError(f"Unexpected persistence read: {entity}")

    session = Mock(spec=AsyncSession)
    session.scalar = AsyncMock(side_effect=scalar)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    provider = Provider(catalog)
    budget = DailyCallBudget(
        configured_budget=budget_limit,
        safety_reserve_percent=0,
        clock=clock,
        provider=MarketDataProvider.EODHD,
    )
    async with httpx.AsyncClient(
        base_url="https://eodhd.invalid/api", transport=httpx.MockTransport(provider.respond)
    ) as http:
        service = ReferenceMarketDataService(
            session,
            client=EodhdClient(
                settings=EodhdSettings(enabled=True, api_key=SecretStr("fixture-key")), client=http
            ),
            call_budget=budget,
            retry_policy=RetryPolicy(clock=clock, sleeper=clock, random=Random(0)),
            rate_limiter=TokenBucketRateLimiter(
                requests_per_second=2, burst_capacity=1, clock=clock, sleeper=clock
            ),
        )
        yield Runtime(service, mapping, session, provider, budget, clock)


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol,currency", [("GSPC", "USD"), ("GDAXI", "EUR")])
async def test_index_validation_uses_exact_catalog_identity_not_fuzzy_search(symbol, currency):
    async with runtime([index_row(Code=symbol, Currency=currency)], symbol=symbol) as run:
        result = await run.validate()

        assert result is run.mapping
        assert result.status is MappingStatus.ACTIVE
        assert result.version == 2
        assert (
            result.validated_at is not None and result.validated_at.utcoffset().total_seconds() == 0
        )
        assert "catalog" in result.validation_message.lower()
        assert "Search API" not in result.validation_message
        assert f"currency={currency}" in result.validation_message
        assert result.id == MAPPING and result.market_data_instrument_id == INSTRUMENT
        assert result.listing_id is None
        assert run.provider.paths == [CATALOG_PATH]
        assert run.provider.requests[0].url.params["symbols"] == symbol
        assert await run.budget.usage() == 1
        assert run.added == []
        run.session.commit.assert_awaited_once()
        run.session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_index_identity_comparison_and_provider_currency_normalization_are_explicit():
    async with runtime(
        [index_row(Code="gspc", Exchange="indx", Type="Index", Currency=" eur ")]
    ) as run:
        result = await run.validate()

        assert result.status is MappingStatus.ACTIVE
        assert "currency=EUR" in result.validation_message
        assert result.provider_symbol == "GSPC" and result.provider_exchange_code == "INDX"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "catalog",
    [
        pytest.param([], id="empty-catalog"),
        pytest.param(SEARCH_OTHER_INSTRUMENTS, id="observed-fund-and-stock"),
        pytest.param([index_row(Code="GSPCX")], id="similar-symbol"),
        pytest.param([index_row(Exchange="US")], id="same-symbol-other-exchange"),
    ],
)
async def test_absent_exact_index_is_invalid_and_never_replaced(catalog):
    async with runtime(catalog) as run:
        result = await run.validate()

        assert result.status is MappingStatus.INVALID
        assert result.version == 2 and result.validated_at is not None
        assert result.provider_symbol == "GSPC" and result.provider_exchange_code == "INDX"
        assert "catalog" in result.validation_message.lower()
        assert run.provider.paths == [CATALOG_PATH]
        assert run.added == []
        run.session.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", [None, "", "  "])
async def test_index_without_provider_currency_remains_invalid(currency):
    async with runtime([index_row(Currency=currency)]) as run:
        result = await run.validate()

        assert result.status is MappingStatus.INVALID
        assert "currency" in result.validation_message.lower()
        assert result.version == 2
        assert run.provider.paths == [CATALOG_PATH]
        assert run.added == []


@pytest.mark.asyncio
async def test_absent_currency_field_is_not_replaced_by_usd_or_search_metadata():
    row = index_row()
    del row["Currency"]
    async with runtime([row]) as run:
        result = await run.validate()

        assert result.status is MappingStatus.INVALID
        assert "currency" in result.validation_message.lower()
        assert run.provider.paths == [CATALOG_PATH]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "catalog",
    [
        pytest.param([index_row(), index_row()], id="duplicate-exact-rows"),
        pytest.param([index_row(), index_row(Currency="EUR")], id="currency-conflict"),
        pytest.param([index_row(), index_row(Type="ETF")], id="type-conflict"),
        pytest.param([index_row(Type="FUND")], id="fund"),
        pytest.param([index_row(Type="Common Stock")], id="stock"),
        pytest.param([index_row(Type="Unknown")], id="unknown-type"),
        pytest.param([index_row(Currency="Unknown")], id="unknown-currency"),
        pytest.param([index_row(Currency="N/A")], id="unusable-currency"),
    ],
)
async def test_conflicting_or_unusable_index_evidence_cannot_activate_mapping(catalog):
    async with runtime(catalog) as run:
        with pytest.raises(ValueError):
            await run.validate()

        assert run.mapping.status is MappingStatus.DISABLED
        assert run.mapping.version == 1 and run.mapping.validated_at is None
        assert run.provider.paths == [CATALOG_PATH]
        assert run.added == []
        run.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "catalog",
    [
        pytest.param({"data": [index_row()]}, id="wrapped-instead-of-array"),
        pytest.param([None], id="null-row"),
        pytest.param([index_row(Code=123)], id="non-string-code"),
        pytest.param([index_row(Exchange=None)], id="missing-exchange"),
        pytest.param([index_row(Type=None)], id="missing-type"),
        pytest.param([index_row(Type=" ")], id="blank-type"),
        pytest.param([index_row(Currency=123)], id="non-string-currency"),
    ],
)
async def test_malformed_catalog_has_no_mapping_success_or_persistence_commit(catalog):
    async with runtime(catalog) as run:
        with pytest.raises(ValueError):
            await run.validate()

        assert run.mapping.status is MappingStatus.DISABLED
        assert run.mapping.version == 1
        assert run.provider.paths == [CATALOG_PATH]
        assert run.added == []
        run.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_validated_index_import_rechecks_catalog_and_preserves_dates_prices_and_owner():
    async with runtime([index_row(Currency="EUR")]) as run:
        await run.validate()
        run.session.commit.reset_mock()

        result = await run.import_prices()

        assert run.provider.paths == [CATALOG_PATH, CATALOG_PATH, "/api/eod/GSPC.INDX"]
        assert dict(run.provider.requests[-1].url.params) == {
            "from": "2026-11-02",
            "to": "2026-11-06",
            "period": "d",
            "order": "a",
            "api_token": "fixture-key",
            "fmt": "json",
        }
        assert (result.inserted, result.updated, result.unchanged) == (2, 0, 0)
        assert result.market_reference_id == REFERENCE
        assert result.mapping_id == MAPPING and result.market_data_instrument_id == INSTRUMENT
        assert result.currency == "EUR" and result.start_date == START and result.end_date == END
        assert run.mapping.version == 2 and run.mapping.status is MappingStatus.ACTIVE
        assert all(isinstance(row, DailyPriceModel) for row in run.added)
        assert len(run.added) == 2
        first, second = run.added
        for row in (first, second):
            assert row.workspace_id == WORKSPACE and row.market_data_instrument_id == INSTRUMENT
            assert row.listing_id is None and row.currency == "EUR"
            assert row.provider_symbol == "GSPC" and row.provider is MarketDataProvider.EODHD
            assert row.price_type is PriceType.EOD
            assert type(row.trading_date) is date
            assert row.source_updated_at is None
        assert first.trading_date == START and second.trading_date == END
        assert (first.open, first.high, first.low, first.close) == (
            Decimal("100.125"),
            Decimal("102.25"),
            Decimal("99.5"),
            Decimal("101.875"),
        )
        assert first.adjusted_close is None and first.volume is None
        assert second.close == Decimal("102.625")
        assert second.adjusted_close == Decimal("102.625") and second.volume == Decimal("0")
        assert await run.budget.usage() == 3
        assert run.clock.sleeps  # Subsequent calls still pass through the shared rate limiter.
        run.session.commit.assert_awaited_once()
        run.session.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changed_catalog",
    [
        pytest.param([], id="identity-disappeared"),
        pytest.param(SEARCH_OTHER_INSTRUMENTS, id="other-instruments-only"),
        pytest.param([index_row(Exchange="US")], id="exchange-mismatch"),
        pytest.param([index_row(Currency=None)], id="currency-lost"),
        pytest.param([index_row(), index_row(Currency="EUR")], id="new-ambiguity"),
        pytest.param([index_row(Type="ETF")], id="different-instrument-type"),
        pytest.param({"error": "unusable"}, id="malformed-evidence"),
    ],
)
async def test_import_requires_fresh_exact_evidence_before_any_eod_request_or_price_write(
    changed_catalog,
):
    async with runtime([index_row()]) as run:
        await run.validate()
        run.provider.catalog = changed_catalog
        run.session.commit.reset_mock()

        with pytest.raises(ValueError):
            await run.import_prices()

        assert run.provider.paths == [CATALOG_PATH, CATALOG_PATH]
        assert run.mapping.status is MappingStatus.ACTIVE and run.mapping.version == 2
        assert run.added == []
        run.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["validate", "import_prices"])
async def test_index_provider_denial_never_activates_or_fetches_history(operation):
    initial_status = MappingStatus.DISABLED if operation == "validate" else MappingStatus.ACTIVE
    async with runtime([index_row()], status=initial_status) as run:
        run.provider.catalog_statuses = [403]

        with pytest.raises(MarketDataAuthorizationError) as caught:
            await getattr(run, operation)()

        assert caught.value.capability is MarketDataCapability.INSTRUMENT_MAPPING_VALIDATION
        assert run.provider.paths == [CATALOG_PATH]
        assert run.mapping.status is initial_status and run.mapping.version == 1
        assert run.added == []
        run.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_index_catalog_retains_bounded_retry_and_counts_each_attempt():
    async with runtime([index_row()]) as run:
        run.provider.catalog_statuses = [503, 503, 200]
        result = await run.validate()

        assert result.status is MappingStatus.ACTIVE and result.version == 2
        assert run.provider.paths == [CATALOG_PATH] * 3
        assert await run.budget.usage() == 3
        assert run.clock.sleeps
        run.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_index_catalog_retry_exhaustion_does_not_fall_back_or_commit():
    async with runtime([index_row()]) as run:
        run.provider.catalog_statuses = [503, 503, 503]

        with pytest.raises(MarketDataUnavailableError):
            await run.validate()

        assert run.provider.paths == [CATALOG_PATH] * 3
        assert await run.budget.usage() == 3
        assert run.mapping.status is MappingStatus.DISABLED and run.mapping.version == 1
        assert run.added == []
        run.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_exhausted_shared_budget_blocks_catalog_before_transport_and_writes():
    async with runtime([index_row()], budget_limit=1) as run:
        await run.validate()
        run.session.commit.reset_mock()

        with pytest.raises(MarketDataBudgetExhaustedError):
            await run.import_prices()

        assert run.provider.paths == [CATALOG_PATH]
        assert await run.budget.usage() == 1
        assert run.added == []
        run.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_index_reference_keeps_existing_search_and_history_contract():
    async with runtime([], symbol="LEGACY", exchange="US") as run:
        run.provider.search = [
            {"Code": "LEGACY", "Exchange": "US", "Currency": "CAD", "Type": "Common Stock"}
        ]

        validated = await run.validate()
        imported = await run.import_prices()

        assert validated.status is MappingStatus.ACTIVE
        assert "Search API" in validated.validation_message
        assert run.provider.paths == [
            "/api/search/LEGACY",
            "/api/search/LEGACY",
            "/api/eod/LEGACY.US",
        ]
        assert run.provider.requests[0].url.params["exchange"] == "US"
        assert run.provider.requests[0].url.params["limit"] == "20"
        assert imported.currency == "CAD"
        assert all(row.currency == "CAD" and row.listing_id is None for row in run.added)

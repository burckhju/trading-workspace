"""Native PostgreSQL qualification of durable chart setup and owner boundaries.

The real owners, ORM, audits, foreign keys and deferred triggers run in the
dedicated CI database. Only public-provider transport is replaced by fixtures.
No chart price history or current provider coverage is claimed by these tests.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_data_instrument_workspace_postgres import (
    _test_database_url,
)
from tests.unit.backend.providers.eodhd.test_adapter import make_adapter
from tests.unit.backend.providers.eodhd.test_stock_catalog import EXCHANGES

from app.features.market.domain.enums import UnderlyingType
from app.features.market.persistence.models import ListingModel
from app.features.market.service.chart_watchlist import ChartWatchlistService
from app.features.market.service.chart_watchlist_catalog import (
    ChartWatchlistCatalog,
    bundled_chart_watchlist_catalog,
)
from app.features.market.service.service import UnderlyingService
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market.service.types import Actor, CreateListing, CreateUnderlying
from app.features.market.service.unit_of_work import SqlAlchemyMarketUnitOfWork
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel
from app.features.market_data.service.administration import (
    MappingCommand,
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.etf_mapping_validation import EtfCatalogMappingResolver
from app.features.market_data.service.instrument_identity import MarketDataInstrumentIdentityService
from app.features.market_data.service.reference_market_data import ReferenceMarketDataService
from app.features.market_data.service.unit_of_work import SqlAlchemyMarketDataUnitOfWork

ACTOR = Actor("chart-watchlist-test", "Chart watchlist native test")
OWNER_TABLES = (
    "underlyings",
    "listings",
    "market_references",
    "market_data_instruments",
    "provider_instrument_mappings",
    "reference_series_definitions",
    "daily_prices",
    "audit_events",
)


def _catalog(*codes):
    complete = bundled_chart_watchlist_catalog()
    return ChartWatchlistCatalog(
        "NATIVE_CHART_WATCHLIST_V1",
        "Native chart watchlist",
        tuple(item for item in complete.items if item.code in codes),
    )


@asynccontextmanager
async def _database(monkeypatch, catalog=None):
    engine = create_async_engine(_test_database_url())
    catalog = catalog or _catalog("SP500", "ETF_US_XLE", "ETF_US_QQQ")
    adapter, client, _ = make_adapter()
    adapter._clock.now = datetime.now(UTC)
    # Provider quota/retry behavior is qualified separately. Avoid the shared
    # helper's zero-yield sleeper at sub-ULP token refill delays in DB scenarios.
    monkeypatch.setattr(type(adapter._rate_limiter), "acquire", AsyncMock())
    payloads = {
        "/exchanges-list/": EXCHANGES,
        "/exchange-symbol-list/US": [
            {
                "Code": item.ticker,
                "Exchange": "NYSE ARCA" if item.mic == "ARCX" else "NASDAQ",
                "Isin": item.isin,
                "Currency": item.currency,
                "Type": "ETF",
                "Name": item.name,
            }
            for item in catalog.items
            if item.kind == "ETF"
        ],
        "/exchange-symbol-list/INDX": [
            {
                "Code": "GSPC",
                "Exchange": "INDX",
                "Currency": "USD",
                "Type": "INDEX",
                "Name": "S&P 500",
            }
        ],
    }
    client.get_json = AsyncMock(side_effect=lambda path, **_: payloads[path])
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                workspace = uuid4()
                now = datetime.now(UTC)
                await connection.execute(
                    text("INSERT INTO workspaces (id,name,created_at) VALUES (:id,:name,:now)"),
                    {"id": workspace, "name": "Chart watchlist native", "now": now},
                )
                await connection.execute(
                    text(
                        "INSERT INTO currencies "
                        "(code,name,minor_unit,is_active,reference_version,created_at,updated_at) "
                        "VALUES ('USD','US Dollar',2,true,'native-test',:now,:now) "
                        "ON CONFLICT (code) DO UPDATE SET is_active=true"
                    ),
                    {"now": now},
                )
                yield SimpleNamespace(
                    connection=connection,
                    workspace=workspace,
                    catalog=catalog,
                    adapter=adapter,
                    client=client,
                )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


def _session(db):
    return AsyncSession(
        bind=db.connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


def _reference_service(db, session, mapping_id_factory=uuid4):
    return ReferenceMarketDataService(
        session,
        client=db.client,
        call_budget=db.adapter._budget,
        retry_policy=db.adapter._retry,
        rate_limiter=db.adapter._rate_limiter,
        mapping_id_factory=mapping_id_factory,
    )


def _service(db, session):
    return ChartWatchlistService(
        session,
        db.workspace,
        catalog=db.catalog,
        etf_discovery=db.adapter.etf_catalog,
        etf_resolver_factory=EtfCatalogMappingResolver,
        reference_service=_reference_service(db, session),
        reference_service_factory=lambda factory: _reference_service(db, session, factory),
    )


async def _activate(db, session):
    return await _service(db, session).activate(
        catalog_version=db.catalog.catalog_version, confirmed=True, actor=ACTOR
    )


async def _count(db, table, workspace=None):
    # Table names are closed test constants, never application/request input.
    return await db.connection.scalar(
        text(f"SELECT count(*) FROM {table} WHERE workspace_id=:ws"),
        {"ws": workspace or db.workspace},
    )


async def _owner_counts(db):
    return {table: await _count(db, table) for table in OWNER_TABLES}


async def _mappings(db, workspace=None):
    result = await db.connection.execute(
        text(
            "SELECT id,listing_id,market_data_instrument_id,status,version,validated_at,"
            "validation_message,provider_symbol,provider_exchange_code,created_at,updated_at "
            "FROM provider_instrument_mappings WHERE workspace_id=:ws ORDER BY provider_symbol"
        ),
        {"ws": workspace or db.workspace},
    )
    return [dict(row) for row in result.mappings()]


async def _member(db, code):
    result = await db.connection.execute(
        text("SELECT * FROM chart_watchlist_members WHERE workspace_id=:ws AND code=:code"),
        {"ws": db.workspace, "code": code},
    )
    return dict(result.mappings().one())


async def _check_deferred_constraints(db):
    # Outer rollback provides isolation; explicitly force deferred checks so an
    # invalid atomic claim cannot hide until a real application COMMIT in CI.
    await db.connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    await db.connection.execute(text("SET CONSTRAINTS ALL DEFERRED"))


async def _existing_etf(db, session, definition, *, status=None, workspace=None):
    workspace = workspace or db.workspace
    now = datetime.now(UTC)
    await session.execute(
        text(
            "INSERT INTO trading_venues "
            "(id,mic,name,country_code,timezone,is_active,reference_version,version,"
            "created_at,updated_at) "
            "VALUES (:id,:mic,:name,'US','America/New_York',true,'native-test',1,:now,:now) "
            "ON CONFLICT (mic) DO UPDATE SET country_code='US',timezone='America/New_York',"
            "is_active=true"
        ),
        {"id": uuid4(), "mic": definition.mic, "name": definition.exchange_name, "now": now},
    )
    venue_id = await session.scalar(
        text("SELECT id FROM trading_venues WHERE mic=:mic"), {"mic": definition.mic}
    )
    await session.commit()
    underlying = await UnderlyingService(SqlAlchemyMarketUnitOfWork(session)).create(
        CreateUnderlying(
            workspace,
            ACTOR,
            definition.name,
            CreateListing(venue_id, definition.ticker, definition.currency),
            type=UnderlyingType.ETF,
            isin=definition.isin,
        )
    )
    listing = await session.scalar(
        select(ListingModel).where(
            ListingModel.workspace_id == workspace, ListingModel.underlying_id == underlying.id
        )
    )
    instrument = await MarketDataInstrumentIdentityService(session).for_listing(
        workspace_id=workspace, listing_id=listing.id
    )
    await session.commit()
    mapping = None
    if status is not None:
        # An existing administrator-owned state is a fixture, not a watchlist write.
        mapping = ProviderInstrumentMappingModel(
            id=uuid4(),
            workspace_id=workspace,
            listing_id=listing.id,
            market_data_instrument_id=instrument.id,
            provider=MarketDataProvider.EODHD,
            provider_symbol=definition.ticker,
            provider_exchange_code="US",
            status=status,
            validated_at=now if status == MappingStatus.ACTIVE else None,
            validation_message="Existing administrator decision",
            created_at=now,
            updated_at=now,
            version=7,
        )
        session.add(mapping)
        await session.commit()
    return SimpleNamespace(
        underlying_id=underlying.id,
        listing_id=listing.id,
        instrument_id=instrument.id,
        venue_id=venue_id,
        mapping_id=mapping.id if mapping is not None else None,
    )


async def _existing_index(db, session, *, status=None, basis=None, workspace=None):
    workspace = workspace or db.workspace
    reference = await TopDownReferenceAdministrationService(session).ensure_v1_reference(
        workspace, "SP500"
    )
    instrument = await MarketDataInstrumentIdentityService(session).for_market_reference(
        workspace_id=workspace, market_reference_id=reference.id
    )
    await session.commit()
    mapping = None
    definition = None
    if status is not None:
        owner = _reference_service(db, session)
        mapping = await owner.upsert_mapping(
            workspace_id=workspace,
            market_reference_id=reference.id,
            provider_symbol="GSPC",
            provider_exchange_code="INDX",
        )
        if status == MappingStatus.ACTIVE:
            mapping = await owner.validate_mapping(
                workspace_id=workspace, market_reference_id=reference.id
            )
            assert mapping.status == MappingStatus.ACTIVE
        elif status == MappingStatus.INVALID:
            mapping.status = MappingStatus.INVALID
            await session.commit()
        if basis is not None:
            definition = await TopDownReferenceAdministrationService(session).confirm_series_basis(
                workspace_id=workspace,
                market_reference_id=reference.id,
                mapping_id=mapping.id,
                mapping_version=mapping.version,
                return_basis=basis,
                source_url="https://evidence.example/existing-index-basis",
                actor="Existing explicit administrator evidence",
            )
    return SimpleNamespace(
        reference_id=reference.id,
        instrument_id=instrument.id,
        mapping_id=mapping.id if mapping is not None else None,
        definition_id=definition.id if definition is not None else None,
    )


@pytest.mark.asyncio
async def test_activation_only_persists_the_confirmed_31_members_and_survives_new_sessions(
    monkeypatch,
):
    async with _database(monkeypatch, bundled_chart_watchlist_catalog()) as db:
        before = await _owner_counts(db)
        async with _session(db) as session:
            preview = await _service(db, session).read()
            assert not preview.enabled and len(preview.items) == 31
            first = await _activate(db, session)
            assert first.enabled and all(item.setup_status == "PENDING" for item in first.items)
        activation = (
            (
                await db.connection.execute(
                    text("SELECT * FROM chart_watchlists WHERE workspace_id=:ws"),
                    {"ws": db.workspace},
                )
            )
            .mappings()
            .one()
        )
        async with _session(db) as session:
            second = await _activate(db, session)
            read_back = await _service(db, session).read()
        assert [item.code for item in first.items] == [item.code for item in second.items]
        assert read_back.model_dump() == second.model_dump()
        assert await _count(db, "chart_watchlists") == 1
        assert await _count(db, "chart_watchlist_members") == 31
        persisted = (
            (
                await db.connection.execute(
                    text("SELECT * FROM chart_watchlists WHERE workspace_id=:ws"),
                    {"ws": db.workspace},
                )
            )
            .mappings()
            .one()
        )
        assert dict(persisted) == dict(activation)
        assert await _owner_counts(db) == before
        db.client.get_json.assert_not_awaited()
        await _check_deferred_constraints(db)


@pytest.mark.asyncio
async def test_new_setup_uses_real_owners_audits_and_separate_index_and_etf_identities(monkeypatch):
    async with _database(monkeypatch) as db:
        async with _session(db) as session:
            await _activate(db, session)
            for definition in db.catalog.items:
                result = await _service(db, session).configure_item(definition.code, ACTOR)
                assert result.setup_status == "CONFIGURED", result.model_dump()
        await _check_deferred_constraints(db)
        counts = await _owner_counts(db)
        assert counts["underlyings"] == counts["listings"] == 2
        assert counts["market_references"] == counts["reference_series_definitions"] == 1
        assert counts["market_data_instruments"] == counts["provider_instrument_mappings"] == 3
        assert counts["daily_prices"] == 0
        references = (
            await db.connection.execute(
                text("SELECT code,reference_type FROM market_references WHERE workspace_id=:ws"),
                {"ws": db.workspace},
            )
        ).all()
        assert [tuple(row) for row in references] == [("SP500", "INDEX")]
        mappings = await _mappings(db)
        assert all(row["status"] == "ACTIVE" and row["version"] == 2 for row in mappings)
        for definition in db.catalog.items:
            member = await _member(db, definition.code)
            mapping = next(row for row in mappings if row["id"] == member["verified_mapping_id"])
            assert member["created_mapping_id"] == mapping["id"]
            assert member["created_mapping_version"] == member["verified_mapping_version"] == 2
            assert member["verified_provider_symbol"] == mapping["provider_symbol"]
            assert member["verified_provider_exchange_code"] == mapping["provider_exchange_code"]
            assert member["setup_completed_at"] is not None
            if definition.kind == "INDEX":
                assert mapping["listing_id"] is None and member["listing_id"] is None
                assert member["market_reference_id"] is not None
            else:
                assert member["listing_id"] == mapping["listing_id"]
                assert member["market_reference_id"] is None
                audits = (
                    (
                        await db.connection.execute(
                            text(
                                "SELECT id FROM audit_events WHERE workspace_id=:ws "
                                "AND aggregate_type='PROVIDER_MAPPING' AND aggregate_id=:id"
                            ),
                            {"ws": db.workspace, "id": mapping["id"]},
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(audits) == len(set(audits)) == 2
        assert {call.args[0] for call in db.client.get_json.call_args_list} == {
            "/exchanges-list/",
            "/exchange-symbol-list/US",
            "/exchange-symbol-list/INDX",
        }
        calls = db.client.get_json.await_count
        async with _session(db) as restarted:
            service = _service(db, restarted)
            assert all(item.setup_status == "CONFIGURED" for item in (await service.read()).items)
            for definition in db.catalog.items:
                assert (
                    await service.configure_item(definition.code, ACTOR)
                ).setup_status == "CONFIGURED"
        assert await _owner_counts(db) == counts
        assert await _mappings(db) == mappings
        assert db.client.get_json.await_count == calls


@pytest.mark.asyncio
async def test_existing_active_owners_mapping_revisions_and_index_basis_are_reused(monkeypatch):
    async with _database(monkeypatch) as db:
        async with _session(db) as session:
            index = await _existing_index(
                db, session, status=MappingStatus.ACTIVE, basis="PRICE_INDEX"
            )
            etfs = {}
            for definition in db.catalog.items:
                if definition.kind == "ETF":
                    etfs[definition.code] = await _existing_etf(
                        db, session, definition, status=MappingStatus.ACTIVE
                    )
        mappings, counts = await _mappings(db), await _owner_counts(db)
        async with _session(db) as session:
            await _activate(db, session)
            for definition in db.catalog.items:
                result = await _service(db, session).configure_item(definition.code, ACTOR)
                assert result.setup_status == "CONFIGURED", result.model_dump()
                member = await _member(db, definition.code)
                assert member["created_mapping_id"] is None
                assert member["created_mapping_version"] is None
                expected = (
                    index.mapping_id
                    if definition.kind == "INDEX"
                    else etfs[definition.code].mapping_id
                )
                assert member["verified_mapping_id"] == expected
        assert await _mappings(db) == mappings
        assert await _owner_counts(db) == counts
        basis_ids = (
            (
                await db.connection.execute(
                    text("SELECT id FROM reference_series_definitions WHERE workspace_id=:ws"),
                    {"ws": db.workspace},
                )
            )
            .scalars()
            .all()
        )
        assert basis_ids == [index.definition_id]
        await _check_deferred_constraints(db)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ETF", "INDEX"])
@pytest.mark.parametrize("status", [MappingStatus.DISABLED, MappingStatus.INVALID])
async def test_preexisting_inactive_mapping_is_preserved_without_provider_or_owner_writes(
    monkeypatch, kind, status
):
    async with _database(monkeypatch, _catalog("SP500", "ETF_US_XLE")) as db:
        definition = next(item for item in db.catalog.items if item.kind == kind)
        async with _session(db) as session:
            if kind == "ETF":
                await _existing_etf(db, session, definition, status=status)
            else:
                await _existing_index(db, session, status=status)
        mappings, counts = await _mappings(db), await _owner_counts(db)
        async with _session(db) as session:
            await _activate(db, session)
            result = await _service(db, session).configure_item(definition.code, ACTOR)
        assert result.setup_status == "BLOCKED"
        assert result.setup_reason == "EXISTING_INACTIVE_MAPPING_PRESERVED"
        assert await _mappings(db) == mappings
        assert await _owner_counts(db) == counts
        db.client.get_json.assert_not_awaited()
        await _check_deferred_constraints(db)


@pytest.mark.asyncio
@pytest.mark.parametrize("inactive", ["underlying", "listing", "venue", "currency", "reference"])
async def test_local_deactivation_is_not_undone_by_initial_watchlist_setup(monkeypatch, inactive):
    async with _database(monkeypatch, _catalog("SP500", "ETF_US_XLE")) as db:
        async with _session(db) as session:
            if inactive == "reference":
                existing = await _existing_index(db, session)
                table, key, column = "market_references", existing.reference_id, "active"
                code = "SP500"
            else:
                definition = next(item for item in db.catalog.items if item.kind == "ETF")
                existing = await _existing_etf(db, session, definition)
                code = definition.code
                table, key, column = {
                    "underlying": ("underlyings", existing.underlying_id, "lifecycle_status"),
                    "listing": ("listings", existing.listing_id, "lifecycle_status"),
                    "venue": ("trading_venues", existing.venue_id, "is_active"),
                    "currency": ("currencies", "USD", "is_active"),
                }[inactive]
            key_column = "code" if inactive == "currency" else "id"
            value = "INACTIVE" if column == "lifecycle_status" else False
            await session.execute(
                text(f"UPDATE {table} SET {column}=:value WHERE {key_column}=:key"),
                {"value": value, "key": key},
            )
            await session.commit()
        counts = await _owner_counts(db)
        async with _session(db) as session:
            await _activate(db, session)
            result = await _service(db, session).configure_item(code, ACTOR)
        assert result.setup_status == "BLOCKED"
        assert (
            await db.connection.scalar(
                text(f"SELECT {column} FROM {table} WHERE {key_column}=:key"), {"key": key}
            )
            == value
        )
        assert await _owner_counts(db) == counts
        db.client.get_json.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ETF", "INDEX"])
async def test_committed_mapping_claim_resumes_after_interruption_before_validation(
    monkeypatch, kind
):
    async with _database(monkeypatch, _catalog("SP500", "ETF_US_XLE")) as db:
        definition = next(item for item in db.catalog.items if item.kind == kind)
        async with _session(db) as session:
            await _activate(db, session)
        interrupted_owner = (
            EtfCatalogMappingResolver if kind == "ETF" else ReferenceMarketDataService
        )
        method = "validate_mapping"
        with monkeypatch.context() as patch:
            patch.setattr(
                interrupted_owner,
                method,
                AsyncMock(side_effect=RuntimeError("simulated process stop")),
            )
            with pytest.raises(RuntimeError, match="simulated process stop"):
                async with _session(db) as session:
                    await _service(db, session).configure_item(definition.code, ACTOR)
        pending = await _member(db, definition.code)
        mapping = (await _mappings(db))[0]
        assert mapping["status"] == "DISABLED" and mapping["version"] == 1
        assert pending["created_mapping_id"] == mapping["id"]
        assert pending["created_mapping_version"] == 1
        assert pending["verified_mapping_id"] is None and pending["setup_completed_at"] is None
        await _check_deferred_constraints(db)
        async with _session(db) as restarted:
            result = await _service(db, restarted).configure_item(definition.code, ACTOR)
        assert result.setup_status == "CONFIGURED", result.model_dump()
        assert result.mapping.id == mapping["id"] and result.mapping.version == 2
        complete = await _member(db, definition.code)
        assert complete["created_mapping_id"] == complete["verified_mapping_id"] == mapping["id"]
        assert complete["created_mapping_version"] == complete["verified_mapping_version"] == 2
        assert len(await _mappings(db)) == 1
        await _check_deferred_constraints(db)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ETF", "INDEX"])
async def test_failed_mapping_creation_does_not_commit_a_dangling_claim(monkeypatch, kind):
    async with _database(monkeypatch, _catalog("SP500", "ETF_US_XLE")) as db:
        definition = next(item for item in db.catalog.items if item.kind == kind)
        async with _session(db) as session:
            await _activate(db, session)
        owner, method = (
            (ProviderMappingAdministrationService, "create_or_update")
            if kind == "ETF"
            else (ReferenceMarketDataService, "upsert_mapping")
        )
        with monkeypatch.context() as patch:
            patch.setattr(
                owner, method, AsyncMock(side_effect=RuntimeError("simulated create failure"))
            )
            with pytest.raises(RuntimeError, match="simulated create failure"):
                async with _session(db) as session:
                    await _service(db, session).configure_item(definition.code, ACTOR)
        pending = await _member(db, definition.code)
        assert pending["created_mapping_id"] is None and pending["created_mapping_version"] is None
        assert await _mappings(db) == []
        await _check_deferred_constraints(db)
        async with _session(db) as restarted:
            result = await _service(db, restarted).configure_item(definition.code, ACTOR)
        assert result.setup_status == "CONFIGURED", result.model_dump()
        assert len(await _mappings(db)) == 1
        await _check_deferred_constraints(db)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ETF", "INDEX"])
async def test_later_active_mapping_revision_is_blocked_without_automatic_reconfirmation(
    monkeypatch, kind
):
    async with _database(monkeypatch, _catalog("SP500", "ETF_US_XLE")) as db:
        definition = next(item for item in db.catalog.items if item.kind == kind)
        async with _session(db) as session:
            await _activate(db, session)
            original = await _service(db, session).configure_item(definition.code, ACTOR)
            assert original.setup_status == "CONFIGURED", original.model_dump()
        await db.connection.execute(
            text(
                "UPDATE provider_instrument_mappings SET version=version+1,updated_at=:now "
                "WHERE id=:id"
            ),
            {"id": original.mapping.id, "now": datetime.now(UTC)},
        )
        if kind == "INDEX":
            member = await _member(db, definition.code)
            # A separate, explicit administrator confirms the new revision. The
            # original watchlist receipt must still refuse to adopt that revision.
            async with _session(db) as session:
                await TopDownReferenceAdministrationService(session).confirm_series_basis(
                    workspace_id=db.workspace,
                    market_reference_id=member["market_reference_id"],
                    mapping_id=original.mapping.id,
                    mapping_version=original.mapping.version + 1,
                    return_basis="PRICE_INDEX",
                    source_url="https://evidence.example/new-revision",
                    actor="Separate explicit administrator",
                )
        mappings, counts = await _mappings(db), await _owner_counts(db)
        receipt, calls = await _member(db, definition.code), db.client.get_json.await_count
        async with _session(db) as restarted:
            service = _service(db, restarted)
            state = next(
                item for item in (await service.read()).items if item.code == definition.code
            )
            assert state.setup_status == "BLOCKED"
            assert state.setup_reason == "MAPPING_CHANGED_SINCE_WATCHLIST_SETUP"
            result = await service.configure_item(definition.code, ACTOR)
            assert result.setup_reason == "MAPPING_CHANGED_SINCE_WATCHLIST_SETUP"
        assert await _member(db, definition.code) == receipt
        assert await _mappings(db) == mappings and await _owner_counts(db) == counts
        assert db.client.get_json.await_count == calls


@pytest.mark.asyncio
@pytest.mark.parametrize("when", ["before_activation", "after_setup"])
async def test_conflicting_index_basis_is_preserved_and_blocks_setup(monkeypatch, when):
    async with _database(monkeypatch, _catalog("SP500")) as db:
        async with _session(db) as session:
            index = await _existing_index(
                db,
                session,
                status=MappingStatus.ACTIVE,
                basis="TOTAL_RETURN_INDEX" if when == "before_activation" else "PRICE_INDEX",
            )
            await _activate(db, session)
            if when == "after_setup":
                original = await _service(db, session).configure_item("SP500", ACTOR)
                assert original.setup_status == "CONFIGURED", original.model_dump()
                await TopDownReferenceAdministrationService(session).confirm_series_basis(
                    workspace_id=db.workspace,
                    market_reference_id=index.reference_id,
                    mapping_id=original.mapping.id,
                    mapping_version=original.mapping.version,
                    return_basis="TOTAL_RETURN_INDEX",
                    source_url="https://evidence.example/conflicting-index-basis",
                    actor="Separate explicit administrator",
                )
        before = await _mappings(db)
        counts, calls = await _owner_counts(db), db.client.get_json.await_count
        async with _session(db) as restarted:
            result = await _service(db, restarted).configure_item("SP500", ACTOR)
        assert result.setup_status == "BLOCKED"
        assert result.setup_reason == "EXISTING_INDEX_RETURN_BASIS_CONFLICT"
        assert await _mappings(db) == before and await _owner_counts(db) == counts
        assert db.client.get_json.await_count == calls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "link,scope",
    [
        ("listing", "other_workspace"),
        ("reference", "other_workspace"),
        ("created_mapping", "other_workspace"),
        ("verified_mapping", "other_workspace"),
        ("created_mapping", "wrong_owner"),
        ("verified_mapping", "wrong_owner"),
    ],
)
async def test_database_rejects_foreign_workspace_and_wrong_owner_links(monkeypatch, link, scope):
    async with _database(monkeypatch) as db:
        other_workspace = uuid4() if scope == "other_workspace" else db.workspace
        if other_workspace != db.workspace:
            await db.connection.execute(
                text("INSERT INTO workspaces (id,name,created_at) VALUES (:id,:name,:now)"),
                {"id": other_workspace, "name": "Other chart workspace", "now": datetime.now(UTC)},
            )
        definitions = {item.code: item for item in db.catalog.items}
        async with _session(db) as session:
            local = await _existing_etf(db, session, definitions["ETF_US_QQQ"])
            foreign = await _existing_etf(
                db,
                session,
                definitions["ETF_US_XLE"],
                status=MappingStatus.DISABLED,
                workspace=other_workspace,
            )
            foreign_index = await _existing_index(db, session, workspace=other_workspace)
            await _activate(db, session)
        code = "SP500" if link == "reference" else "ETF_US_QQQ"
        with pytest.raises(IntegrityError):
            async with db.connection.begin_nested():
                if link == "listing":
                    updates, values = "listing_id=:foreign", {"foreign": foreign.listing_id}
                elif link == "reference":
                    updates, values = "market_reference_id=:foreign", {
                        "foreign": foreign_index.reference_id
                    }
                elif link == "created_mapping":
                    updates, values = (
                        "listing_id=:local,created_mapping_id=:foreign,created_mapping_version=7",
                        {"local": local.listing_id, "foreign": foreign.mapping_id},
                    )
                else:
                    updates, values = (
                        "listing_id=:local,verified_mapping_id=:foreign,verified_mapping_version=7,"
                        "verified_provider_symbol='XLE',verified_provider_exchange_code='US',"
                        "setup_completed_at=:now",
                        {
                            "local": local.listing_id,
                            "foreign": foreign.mapping_id,
                            "now": datetime.now(UTC),
                        },
                    )
                await db.connection.execute(
                    text(
                        f"UPDATE chart_watchlist_members SET {updates} "
                        "WHERE workspace_id=:ws AND code=:code"
                    ),
                    {"ws": db.workspace, "code": code, **values},
                )
                await db.connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        member = await _member(db, code)
        assert member["created_mapping_id"] is None and member["verified_mapping_id"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ETF", "INDEX"])
async def test_owner_require_absent_preserves_mapping_inserted_after_caller_precheck(
    monkeypatch, kind
):
    async with _database(monkeypatch, _catalog("SP500", "ETF_US_XLE")) as db:
        definition = next(item for item in db.catalog.items if item.kind == kind)
        async with _session(db) as session:
            existing = (
                await _existing_etf(db, session, definition)
                if kind == "ETF"
                else await _existing_index(db, session)
            )
            assert (
                await session.scalar(
                    select(ProviderInstrumentMappingModel.id).where(
                        ProviderInstrumentMappingModel.workspace_id == db.workspace
                    )
                )
                is None
            )
        # Commit in another session after the caller's precheck, before its
        # require_absent owner command. No timing-sensitive sleeps are needed.
        async with _session(db) as competing:
            if kind == "ETF":
                await ProviderMappingAdministrationService(
                    SqlAlchemyMarketDataUnitOfWork(competing),
                    instrument_identity=MarketDataInstrumentIdentityService(competing),
                ).create_or_update(
                    MappingCommand(
                        db.workspace,
                        existing.listing_id,
                        MarketDataProvider.EODHD,
                        definition.ticker,
                        "US",
                        ACTOR.id,
                        "Competing administrator",
                    )
                )
            else:
                await _reference_service(db, competing).upsert_mapping(
                    workspace_id=db.workspace,
                    market_reference_id=existing.reference_id,
                    provider_symbol="GSPC",
                    provider_exchange_code="INDX",
                )
        before, counts = await _mappings(db), await _owner_counts(db)
        with pytest.raises(ValueError, match="PROVIDER_MAPPING_ALREADY_EXISTS"):
            async with _session(db) as guarded:
                if kind == "ETF":
                    await ProviderMappingAdministrationService(
                        SqlAlchemyMarketDataUnitOfWork(guarded),
                        instrument_identity=MarketDataInstrumentIdentityService(guarded),
                    ).create_or_update(
                        MappingCommand(
                            db.workspace,
                            existing.listing_id,
                            MarketDataProvider.EODHD,
                            definition.ticker,
                            "US",
                            ACTOR.id,
                            ACTOR.display_name,
                            require_absent=True,
                        )
                    )
                else:
                    await _reference_service(db, guarded).upsert_mapping(
                        workspace_id=db.workspace,
                        market_reference_id=existing.reference_id,
                        provider_symbol="GSPC",
                        provider_exchange_code="INDX",
                        require_absent=True,
                    )
        assert await _mappings(db) == before
        assert await _owner_counts(db) == counts
        await _check_deferred_constraints(db)

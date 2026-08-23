"""Tests for the application dependency container."""

import asyncio
from unittest.mock import AsyncMock

from fastapi import FastAPI, Request

from app.core.config import Environment, Settings
from app.core.di import (
    ApplicationContainer,
    get_application_settings,
    get_container,
    get_database_manager,
)


def _settings() -> Settings:
    return Settings(
        environment=Environment.TEST,
        database_url="postgresql+asyncpg://localhost/trading_workspace_test",
    )


def test_container_builds_one_technical_dependency_graph() -> None:
    settings = _settings()

    container = ApplicationContainer.build(settings)

    assert container.settings is settings
    assert str(container.database.url) == settings.database_url


def test_container_closes_owned_database_manager() -> None:
    container = ApplicationContainer.build(_settings())
    container.database.dispose = AsyncMock()  # type: ignore[method-assign]

    asyncio.run(container.close())

    container.database.dispose.assert_awaited_once_with()


def test_fastapi_dependencies_resolve_from_application_state() -> None:
    application = FastAPI()
    container = ApplicationContainer.build(_settings())
    application.state.container = container
    request = Request({"type": "http", "app": application})

    assert get_container(request) is container
    assert get_application_settings(request) is container.settings
    assert get_database_manager(request) is container.database


def test_disabled_eodhd_does_not_require_api_key() -> None:
    container = ApplicationContainer.build(_settings())

    assert container.eodhd is None


def test_enabled_eodhd_requires_api_key() -> None:
    import pytest

    from app.features.market_data.service.errors import MarketDataConfigurationError

    settings = Settings(
        _env_file=None,
        environment=Environment.TEST,
        database_url="postgresql+asyncpg://localhost/trading_workspace_test",
        market_data={"eodhd": {"enabled": True}},
    )

    with pytest.raises(MarketDataConfigurationError):
        ApplicationContainer.build(settings)


def test_enabled_eodhd_builds_and_closes_shared_runtime() -> None:
    settings = Settings(
        _env_file=None,
        environment=Environment.TEST,
        database_url="postgresql+asyncpg://localhost/trading_workspace_test",
        market_data={"eodhd": {"enabled": True, "api_key": "paid-secret"}},
    )
    container = ApplicationContainer.build(settings)
    assert container.eodhd is not None
    container.eodhd.http_client.aclose = AsyncMock()  # type: ignore[method-assign]
    container.database.dispose = AsyncMock()  # type: ignore[method-assign]

    asyncio.run(container.close())

    container.eodhd.http_client.aclose.assert_awaited_once_with()
    container.database.dispose.assert_awaited_once_with()


def test_provider_mapping_service_is_available_when_eodhd_is_disabled() -> None:
    container = ApplicationContainer.build(_settings())

    async def exercise() -> None:
        async with container.provider_mapping_service() as service:
            assert service._resolver is None

    asyncio.run(exercise())


def test_daily_price_import_service_stays_fail_closed_when_eodhd_is_disabled() -> None:
    import pytest

    from app.features.market_data.service.errors import MarketDataConfigurationError

    container = ApplicationContainer.build(_settings())

    async def exercise() -> None:
        async with container.daily_price_import_service():
            pass

    with pytest.raises(MarketDataConfigurationError, match="EODHD provider is disabled"):
        asyncio.run(exercise())

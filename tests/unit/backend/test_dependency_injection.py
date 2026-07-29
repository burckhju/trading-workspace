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

"""FastAPI dependencies for application-level technical services."""

from typing import cast

from fastapi import Request

from app.core.config import Settings
from app.core.di.container import ApplicationContainer
from app.database import DatabaseManager


def get_container(request: Request) -> ApplicationContainer:
    """Return the dependency container attached to the application."""

    return cast(ApplicationContainer, request.app.state.container)


def get_application_settings(request: Request) -> Settings:
    """Resolve immutable application settings through FastAPI DI."""

    return get_container(request).settings


def get_database_manager(request: Request) -> DatabaseManager:
    """Resolve the process-wide database manager through FastAPI DI."""

    return get_container(request).database

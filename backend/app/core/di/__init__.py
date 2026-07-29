"""Application dependency injection infrastructure."""

from app.core.di.container import ApplicationContainer
from app.core.di.dependencies import (
    get_application_settings,
    get_container,
    get_database_manager,
)

__all__ = [
    "ApplicationContainer",
    "get_application_settings",
    "get_container",
    "get_database_manager",
]

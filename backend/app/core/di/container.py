"""Application-level dependency container."""

from dataclasses import dataclass

from app.core.config import Settings
from app.database import DatabaseManager


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Own process-wide technical dependencies and their lifecycle."""

    settings: Settings
    database: DatabaseManager

    @classmethod
    def build(cls, settings: Settings) -> "ApplicationContainer":
        """Build the technical dependency graph for one application instance."""

        return cls(settings=settings, database=DatabaseManager(settings))

    async def close(self) -> None:
        """Release resources owned by the container."""

        await self.database.dispose()

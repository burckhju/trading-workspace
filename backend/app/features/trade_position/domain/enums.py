"""FT-009 Trade & Position domain enumerations."""

from enum import StrEnum


class TradeOrigin(StrEnum):
    WORKSPACE_SELECTION = "WORKSPACE_SELECTION"
    EXTERNAL = "EXTERNAL"

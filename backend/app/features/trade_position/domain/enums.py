"""Trade & Position domain enumerations."""

from enum import StrEnum


class TradeOrigin(StrEnum):
    WORKSPACE_SELECTION = "WORKSPACE_SELECTION"
    EXTERNAL = "EXTERNAL"


class ExecutionSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"

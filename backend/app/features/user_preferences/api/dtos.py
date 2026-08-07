"""REST DTOs for user preferences."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreatePreferenceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    value: dict[str, Any]


class PreferenceResponse(BaseModel):
    id: UUID
    kind: str
    name: str
    value: dict[str, Any]
    created_at: datetime
    updated_at: datetime

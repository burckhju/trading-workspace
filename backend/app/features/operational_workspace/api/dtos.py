"""REST contracts for the operational workspace read model."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OperationalActionResponse(BaseModel):
    id: str
    source_feature: str
    action_type: str
    priority: str
    state: str
    title: str
    detail: str
    resource_type: str
    resource_id: UUID
    next_action: str
    target: str
    occurred_at: datetime | None


class OperationalWorkspaceResponse(BaseModel):
    generated_at: datetime
    actions: list[OperationalActionResponse]

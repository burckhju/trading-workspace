"""Central request identity abstraction."""

from app.core.identity.context import (
    DEFAULT_ACTOR_NAME,
    LOCAL_ACTOR_ID,
    RequestIdentity,
    get_request_identity,
)

__all__ = [
    "DEFAULT_ACTOR_NAME",
    "LOCAL_ACTOR_ID",
    "RequestIdentity",
    "get_request_identity",
]

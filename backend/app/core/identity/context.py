"""Request identity resolved at the application boundary.

This module does not authenticate callers. It normalizes the currently trusted
request headers and provides an explicit local-development fallback until an
authentication adapter is introduced.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Header

LOCAL_ACTOR_ID = "local-user"
DEFAULT_ACTOR_NAME = "Trading Workspace User"


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    """Identity metadata available to application services for one request."""

    actor_id: str
    actor_name: str
    authenticated: bool = False


def _normalized(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def get_request_identity(
    actor_id: Annotated[str | None, Header(alias="X-Actor-ID")] = None,
    actor_name: Annotated[str | None, Header(alias="X-Actor-Name")] = None,
) -> RequestIdentity:
    """Resolve request identity without claiming authentication.

    Header trust is transitional. A future authentication adapter can replace
    this dependency without changing feature routers or services.
    """

    return RequestIdentity(
        actor_id=_normalized(actor_id) or LOCAL_ACTOR_ID,
        actor_name=_normalized(actor_name) or DEFAULT_ACTOR_NAME,
        authenticated=False,
    )

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.identity import LOCAL_ACTOR_ID, RequestIdentity, get_request_identity


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/identity")
    async def identity(
        value: Annotated[RequestIdentity, Depends(get_request_identity)],
    ) -> dict[str, object]:
        return {
            "actor_id": value.actor_id,
            "actor_name": value.actor_name,
            "authenticated": value.authenticated,
        }

    return app


def test_request_identity_uses_explicit_headers() -> None:
    response = TestClient(_app()).get(
        "/identity",
        headers={"X-Actor-ID": " user-42 ", "X-Actor-Name": " Ada "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "actor_id": "user-42",
        "actor_name": "Ada",
        "authenticated": False,
    }


def test_request_identity_uses_explicit_local_fallback() -> None:
    response = TestClient(_app()).get("/identity")

    assert response.status_code == 200
    assert response.json()["actor_id"] == LOCAL_ACTOR_ID
    assert response.json()["authenticated"] is False

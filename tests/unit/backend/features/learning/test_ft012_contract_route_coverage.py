from __future__ import annotations

from fastapi.routing import APIRoute
from test_trade_link_api import _make_app


def _routes() -> dict[tuple[str, str], APIRoute]:
    result: dict[tuple[str, str], APIRoute] = {}

    app = _make_app()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for method in route.methods:
            result[(method, route.path)] = route

    return result


def test_ft012_lesson_contract_routes_present() -> None:
    routes = _routes()

    expected = {
        ("POST", "/api/v1/learning/lessons"),
        ("GET", "/api/v1/learning/lessons/{lesson_id}"),
        ("GET", "/api/v1/learning/lessons"),
        ("PATCH", "/api/v1/learning/lessons/{lesson_id}/title"),
        ("PUT", "/api/v1/learning/lessons/{lesson_id}/tags"),
        ("POST", "/api/v1/learning/lessons/{lesson_id}/versions"),
        (
            "POST",
            "/api/v1/learning/lessons/{lesson_id}/state-transitions",
        ),
        ("GET", "/api/v1/learning/lessons/{lesson_id}/history"),
        ("GET", "/api/v1/learning/lessons/{lesson_id}/evidence"),
        (
            "POST",
            "/api/v1/learning/lessons/{lesson_id}/review-signals",
        ),
        (
            "GET",
            "/api/v1/learning/lessons/{lesson_id}/review-signals",
        ),
        (
            "POST",
            "/api/v1/learning/lesson-review-signals/{signal_id}/resolve-unchanged",
        ),
        (
            "POST",
            "/api/v1/learning/lesson-review-signals/{signal_id}/resolve-new-version",
        ),
        (
            "POST",
            "/api/v1/learning/lesson-review-signals/{signal_id}/resolve-retired",
        ),
        ("GET", "/api/v1/learning/lesson-suggestions"),
        (
            "GET",
            "/api/v1/learning/lesson-suggestions/{suggestion_id}",
        ),
        (
            "POST",
            "/api/v1/learning/lesson-suggestions/{suggestion_id}/reject",
        ),
        (
            "POST",
            "/api/v1/learning/lesson-suggestions/{suggestion_id}/confirm",
        ),
        ("GET", "/api/v1/learning/lesson-tags"),
    }

    assert expected <= set(routes)


def test_state_transition_contract_status_is_200() -> None:
    route = _routes()[
        (
            "POST",
            "/api/v1/learning/lessons/{lesson_id}/state-transitions",
        )
    ]

    assert route.status_code == 200

"""Public stateless contract; no database, provider transport or notification delivery."""

import copy

import httpx
import pytest
from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.features.position_monitoring.api.iv import router


@pytest.fixture
def payload():
    return dict(
        basis="HYPOTHETICAL_ASSUMPTIONS",
        product_type="VANILLA_WARRANT",
        exercise_style="EUROPEAN",
        direction="CALL",
        spot="100",
        strike="100",
        ratio="0.1",
        remaining_days="365",
        iv_percent="20",
        rate_percent="5",
        dividend_yield_percent="0",
        currency="EUR",
        underlying_currency="EUR",
        strike_currency="EUR",
        quanto=False,
        dividend_model="CONTINUOUS_YIELD",
        ratio_convention="UNDERLYING_UNITS_PER_WARRANT",
        scenario=dict(
            underlying_change_percent="-5", iv_change_pp="-5", elapsed_days="7", quantity="100"
        ),
    )


@pytest.fixture
async def client():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as value:
        yield value


async def test_stateless_scenario_contract_and_hypothetical_inverse(client, payload):
    response = await client.post("/risk/iv/model-preview", json=payload)
    assert response.status_code == 200
    value = response.json()
    assert value["status"] == "HYPOTHETICAL" and not value["execution_usable"]
    assert value["iv_origin"] == "USER_ASSUMPTION"
    assert value["inputs"]["iv_decimal"] == "0.2"
    assert float(value["baseline_price"]) == pytest.approx(1.045058357218556)
    assert float(value["position_change"]) < 0
    assert value["scenario"]["iv_change_pp"] == "-5"
    assert value == (await client.post("/risk/iv/model-preview", json=payload)).json()
    payload.pop("iv_percent")
    payload["calibration_price"] = "1.045058357218556"
    inverse = await client.post("/risk/iv/model-preview", json=payload)
    assert inverse.status_code == 200
    assert inverse.json()["iv_origin"] == "HYPOTHETICAL_PRICE_INVERSION"
    assert float(inverse.json()["inputs"]["iv_decimal"]) == pytest.approx(0.2, abs=1e-12)


@pytest.mark.parametrize(
    "changes",
    [
        {"basis": "CURRENT_MARKET"},
        {"product_type": "KNOCK_OUT"},
        {"exercise_style": "AMERICAN"},
        {"spot": "NaN"},
        {"iv_percent": "Infinity"},
        {"spot": "0"},
        {"ratio": "0"},
        {"quanto": True},
        {"quanto": "false"},
        {"underlying_currency": "USD"},
        {"strike_currency": "USD"},
        {"dividend_model": "DISCRETE"},
        {"iv_percent": None},
        {"calibration_price": "1"},
        {"remaining_days": "0"},
        {"execution_usable": True},
        {
            "scenario": {
                "quantity": 0,
                "iv_change_pp": -5,
                "elapsed_days": 1,
                "underlying_change_percent": 0,
            }
        },
    ],
)
async def test_invalid_or_unsupported_requests_are_422_not_silent_fallback(
    client, payload, changes
):
    payload.update(changes)
    assert (await client.post("/risk/iv/model-preview", json=payload)).status_code == 422


async def test_missing_assumptions_and_concrete_solver_error(client, payload):
    for field in ("rate_percent", "dividend_yield_percent", "ratio_convention", "basis"):
        missing = copy.deepcopy(payload)
        missing.pop(field)
        assert (await client.post("/risk/iv/model-preview", json=missing)).status_code == 422
    payload.pop("iv_percent")
    payload["calibration_price"] = "11"
    response = await client.post("/risk/iv/model-preview", json=payload)
    assert response.status_code == 422
    assert response.json()["message"] == "PRICE_OUTSIDE_MODEL_BOUNDS"

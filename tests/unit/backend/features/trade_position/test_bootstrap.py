from app.main import create_application


def test_trade_position_router_is_registered_in_application() -> None:
    app = create_application()

    paths = {
        route.path
        for route in app.routes
    }

    assert "/api/v1/trade-position/purchases/from-selection" in paths
    assert "/api/v1/trade-position/purchases/external" in paths
    assert "/api/v1/trade-position/trades/{trade_id}/purchases" in paths

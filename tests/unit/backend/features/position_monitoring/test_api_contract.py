from app.main import create_application


def test_position_monitoring_read_routes_are_registered() -> None:
    application = create_application()
    routes = {route.path for route in application.routes}

    assert "/api/v1/position-monitoring/trades/{trade_id}/health" in routes
    assert "/api/v1/position-monitoring/trades/{trade_id}/analytics" in routes
    assert "/api/v1/position-monitoring/trades/{trade_id}/phase" in routes
    assert "/api/v1/position-monitoring/trades/{trade_id}/scores" in routes
    assert "/api/v1/position-monitoring/trades/{trade_id}/dynamic-stop" in routes
    assert "/api/v1/position-monitoring/trades/{trade_id}/alert-projection" in routes
    assert "/api/v1/position-monitoring/trades/{trade_id}/product-valuation" in routes

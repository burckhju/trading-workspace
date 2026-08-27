from app.features.market.api.reference_market_data_router import router


def test_reference_live_routes_are_registered() -> None:
    paths = {route.path for route in router.routes}
    assert len(paths) == 3
    assert any(path.endswith("/provider-mapping/eodhd") for path in paths)
    assert any(path.endswith("/provider-mapping/eodhd/validate") for path in paths)
    assert any(path.endswith("/daily-prices/import") for path in paths)

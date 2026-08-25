from app.features.market.api.top_down_router import router


def test_reference_market_data_and_analysis_routes_are_exposed() -> None:
    paths = {route.path for route in router.routes}

    assert "/api/v1/top-down-reference-data/readiness" in paths
    assert (
        "/api/v1/top-down-reference-data/market-references/{reference_id}/provider-mapping/eodhd"
        in paths
    )
    assert (
        "/api/v1/top-down-reference-data/market-references/{reference_id}/provider-mapping/eodhd/validate"
        in paths
    )
    assert (
        "/api/v1/top-down-reference-data/market-references/{reference_id}/daily-prices/import"
        in paths
    )
    assert (
        "/api/v1/top-down-reference-data/market-references/{reference_id}/analyses" in paths
    )
    assert (
        "/api/v1/top-down-reference-data/market-references/{reference_id}/analyses/{analysis_id}/run"
        in paths
    )

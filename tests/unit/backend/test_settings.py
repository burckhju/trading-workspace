from app.core.config import Environment, Settings


def test_settings_load_prefixed_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_WORKSPACE_ENVIRONMENT", "test")
    monkeypatch.setenv("TRADING_WORKSPACE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("TRADING_WORKSPACE_DOCUMENTATION_ENABLED", "true")

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.TEST
    assert settings.log_level == "DEBUG"
    assert settings.documentation_enabled is True


def test_settings_load_nested_eodhd_configuration(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED", "true")
    monkeypatch.setenv("TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY", "secret")
    monkeypatch.setenv(
        "TRADING_WORKSPACE_MARKET_DATA__EODHD__BASE_URL", "https://example.test/api/"
    )

    settings = Settings(_env_file=None)

    assert settings.market_data.eodhd.enabled is True
    assert settings.market_data.eodhd.api_key is not None
    assert settings.market_data.eodhd.api_key.get_secret_value() == "secret"
    assert settings.market_data.eodhd.base_url == "https://example.test/api"
    assert "secret" not in repr(settings.market_data.eodhd)


def test_paid_account_operational_limits_are_configurable(monkeypatch) -> None:
    monkeypatch.setenv(
        "TRADING_WORKSPACE_MARKET_DATA__EODHD__DAILY_CALL_LIMIT", "250000"
    )
    monkeypatch.setenv(
        "TRADING_WORKSPACE_MARKET_DATA__EODHD__DAILY_CALL_SAFETY_RESERVE", "5000"
    )
    monkeypatch.setenv(
        "TRADING_WORKSPACE_MARKET_DATA__EODHD__REQUESTS_PER_MINUTE", "1500"
    )
    monkeypatch.setenv(
        "TRADING_WORKSPACE_MARKET_DATA__EODHD__RATE_LIMIT_BURST_CAPACITY", "25"
    )

    settings = Settings(_env_file=None)
    eodhd = settings.market_data.eodhd

    assert eodhd.daily_call_limit == 250000
    assert eodhd.daily_call_safety_reserve == 5000
    assert eodhd.requests_per_minute == 1500
    assert eodhd.rate_limit_burst_capacity == 25

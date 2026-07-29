from app.core.config import Environment, Settings


def test_settings_load_prefixed_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_WORKSPACE_ENVIRONMENT", "test")
    monkeypatch.setenv("TRADING_WORKSPACE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("TRADING_WORKSPACE_DOCUMENTATION_ENABLED", "true")

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.TEST
    assert settings.log_level == "DEBUG"
    assert settings.documentation_enabled is True

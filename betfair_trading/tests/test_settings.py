from pathlib import Path

from betfair_trading.config.settings import Settings
from betfair_trading.core.modes import TradingMode


def test_settings_from_env_defaults_to_paper_with_no_env(monkeypatch):
    for key in [
        "BETFAIR_USERNAME",
        "BETFAIR_PASSWORD",
        "BETFAIR_APP_KEY",
        "BETFAIR_CERT_PATH",
        "BETFAIR_CERT_KEY_PATH",
        "FOOTBALL_DATA_API_KEY",
        "EXTERNAL_ODDS_API_KEY",
        "TRADING_DB_PATH",
        "TRADING_MODE",
        "LIVE_TRADING_CONFIRMED",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_env()

    assert settings.trading_mode is TradingMode.PAPER
    assert settings.live_trading_confirmed_raw is None
    assert not settings.betfair.is_configured


def test_settings_from_env_reads_all_betfair_credentials(monkeypatch):
    monkeypatch.setenv("BETFAIR_USERNAME", "user")
    monkeypatch.setenv("BETFAIR_PASSWORD", "pass")
    monkeypatch.setenv("BETFAIR_APP_KEY", "app-key")
    monkeypatch.setenv("BETFAIR_CERT_PATH", "/certs/client.crt")
    monkeypatch.setenv("BETFAIR_CERT_KEY_PATH", "/certs/client.key")

    settings = Settings.from_env()

    assert settings.betfair.is_configured
    assert settings.betfair.username == "user"


def test_settings_db_path_override(monkeypatch):
    monkeypatch.setenv("TRADING_DB_PATH", "/tmp/custom/trading.duckdb")
    settings = Settings.from_env()
    assert settings.db_path == Path("/tmp/custom/trading.duckdb")


def test_settings_live_mode_from_env(monkeypatch):
    monkeypatch.setenv("TRADING_MODE", "LIVE")
    monkeypatch.setenv("LIVE_TRADING_CONFIRMED", "YES")
    settings = Settings.from_env()
    assert settings.trading_mode is TradingMode.LIVE
    assert settings.live_trading_confirmed_raw == "YES"

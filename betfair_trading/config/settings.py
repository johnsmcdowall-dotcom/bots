"""Env-driven settings. The only module allowed to read Betfair/data-feed
secrets out of os.environ — everything else receives an already-built
Settings (or a client built from one), which keeps credentials out of
every other module and out of test code entirely.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from betfair_trading.core.modes import TradingMode

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "var" / "trading.duckdb"


@dataclass(frozen=True)
class BetfairCredentials:
    username: str | None
    password: str | None
    app_key: str | None
    cert_path: str | None
    cert_key_path: str | None

    @property
    def is_configured(self) -> bool:
        return all(
            [self.username, self.password, self.app_key, self.cert_path, self.cert_key_path]
        )


@dataclass(frozen=True)
class Settings:
    betfair: BetfairCredentials
    football_data_api_key: str | None
    external_odds_api_key: str | None
    db_path: Path
    trading_mode: TradingMode
    live_trading_confirmed_raw: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        betfair = BetfairCredentials(
            username=os.environ.get("BETFAIR_USERNAME"),
            password=os.environ.get("BETFAIR_PASSWORD"),
            app_key=os.environ.get("BETFAIR_APP_KEY"),
            cert_path=os.environ.get("BETFAIR_CERT_PATH"),
            cert_key_path=os.environ.get("BETFAIR_CERT_KEY_PATH"),
        )
        db_path_raw = os.environ.get("TRADING_DB_PATH")
        return cls(
            betfair=betfair,
            football_data_api_key=os.environ.get("FOOTBALL_DATA_API_KEY"),
            external_odds_api_key=os.environ.get("EXTERNAL_ODDS_API_KEY"),
            db_path=Path(db_path_raw) if db_path_raw else DEFAULT_DB_PATH,
            trading_mode=TradingMode.from_env_value(os.environ.get("TRADING_MODE")),
            live_trading_confirmed_raw=os.environ.get("LIVE_TRADING_CONFIRMED"),
        )

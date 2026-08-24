"""Betfair certificate-login session management, wrapping betfairlightweight.

Not exercised against the live Betfair API in this environment (no
credentials here) — structured so it can be integration-tested wherever
real credentials/certs exist, without any calling code changing.
`betfairlightweight` is imported lazily inside methods, never at module
import time, so the rest of the platform can be imported and unit-tested
without the dependency installed and without ever touching the network.
"""

from __future__ import annotations

from typing import Any

from betfair_trading.config.settings import BetfairCredentials


class BetfairConfigError(RuntimeError):
    """Raised when Betfair credentials/certs are missing or incomplete."""


class BetfairSession:
    """Owns login/logout and the underlying betfairlightweight trading client."""

    def __init__(self, credentials: BetfairCredentials):
        if not credentials.is_configured:
            raise BetfairConfigError(
                "Betfair credentials are not fully configured. Set "
                "BETFAIR_USERNAME, BETFAIR_PASSWORD, BETFAIR_APP_KEY, "
                "BETFAIR_CERT_PATH, BETFAIR_CERT_KEY_PATH in .env (see .env.example)."
            )
        self._credentials = credentials
        self._trading: Any = None

    def login(self) -> Any:
        """Perform certificate login; return the betfairlightweight APIClient.

        Idempotent per-process: a second call reuses the client object and
        re-logs-in (betfairlightweight session tokens expire and must be
        refreshed periodically by the caller — that refresh policy belongs
        to whichever long-lived process holds this session, not here).
        """
        import betfairlightweight

        if self._trading is None:
            self._trading = betfairlightweight.APIClient(
                username=self._credentials.username,
                password=self._credentials.password,
                app_key=self._credentials.app_key,
                certs=self._credentials.cert_path,
            )
        self._trading.login()
        return self._trading

    def logout(self) -> None:
        if self._trading is not None:
            self._trading.logout()

    def __enter__(self) -> Any:
        return self.login()

    def __exit__(self, *exc_info: object) -> None:
        self.logout()

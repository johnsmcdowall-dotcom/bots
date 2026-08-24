"""Typed REST wrapper over the Betfair Betting/Account APIs.

Every method here takes/returns this platform's own dataclasses
(betfair.models), never betfairlightweight's raw response objects — that
translation happens once, in `_convert_market_book` etc., so nothing
downstream (storage, replay, strategies) needs to know betfairlightweight
exists.

Not exercised against the live API in this environment (no credentials) —
the conversion helpers (`_convert_market_book`) are pure functions and are
unit-tested against hand-built fake betfairlightweight-shaped objects so
the translation logic itself has coverage today.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from betfair_trading.betfair.auth import BetfairSession
from betfair_trading.betfair.models import (
    MarketSnapshot,
    MarketStatus,
    Order,
    PriceLevel,
    RunnerLadder,
    RunnerStatus,
)


def _convert_market_book(raw: Any) -> MarketSnapshot:
    """Convert one betfairlightweight MarketBook (or a fake with the same
    attribute shape) into a MarketSnapshot.
    """
    runners = tuple(
        RunnerLadder(
            selection_id=str(r.selection_id),
            status=RunnerStatus(r.status),
            back=tuple(
                PriceLevel(p.price, p.size) for p in (r.ex.available_to_back or [])
            ),
            lay=tuple(
                PriceLevel(p.price, p.size) for p in (r.ex.available_to_lay or [])
            ),
            last_traded_price=r.last_price_traded,
            total_matched=r.total_matched or 0.0,
        )
        for r in raw.runners
    )
    return MarketSnapshot(
        market_id=raw.market_id,
        timestamp=getattr(raw, "publish_time", None) or datetime.now(timezone.utc),
        status=MarketStatus(raw.status),
        in_play=bool(raw.inplay),
        total_matched=raw.total_matched or 0.0,
        runners=runners,
    )


class BetfairClient:
    """High-level Betfair REST operations used by ingestion and execution."""

    def __init__(self, session: BetfairSession):
        self._session = session

    def _trading(self) -> Any:
        return self._session.login()

    def list_market_catalogue(self, filter_: dict[str, Any], max_results: int = 100) -> list[Any]:
        import betfairlightweight

        market_filter = betfairlightweight.filters.market_filter(**filter_)
        return self._trading().betting.list_market_catalogue(
            filter=market_filter, max_results=max_results
        )

    def list_market_books(self, market_ids: Iterable[str]) -> list[MarketSnapshot]:
        raw_books = self._trading().betting.list_market_book(market_ids=list(market_ids))
        return [_convert_market_book(book) for book in raw_books]

    def place_orders(self, market_id: str, orders: Iterable[Order]) -> Any:
        import betfairlightweight

        instructions = [
            betfairlightweight.filters.place_instruction(
                order_type="LIMIT",
                selection_id=order.selection_id,
                side=order.side,
                limit_order=betfairlightweight.filters.limit_order(
                    size=order.size,
                    price=order.price,
                    persistence_type=order.persistence_type,
                ),
            )
            for order in orders
        ]
        return self._trading().betting.place_orders(market_id=market_id, instructions=instructions)

    def cancel_orders(self, market_id: str, bet_ids: Iterable[str]) -> Any:
        import betfairlightweight

        instructions = [
            betfairlightweight.filters.cancel_instruction(bet_id=bet_id) for bet_id in bet_ids
        ]
        return self._trading().betting.cancel_orders(market_id=market_id, instructions=instructions)

    def list_current_orders(self, market_ids: Iterable[str] | None = None) -> Any:
        return self._trading().betting.list_current_orders(market_ids=list(market_ids) if market_ids else None)

    def list_cleared_orders(self, market_ids: Iterable[str] | None = None) -> Any:
        import betfairlightweight

        return self._trading().betting.list_cleared_orders(
            bet_status="SETTLED",
            market_ids=list(market_ids) if market_ids else None,
        )

    def account_funds(self) -> Any:
        return self._trading().account.get_account_funds()

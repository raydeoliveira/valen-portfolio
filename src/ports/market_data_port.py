"""Market data port — abstract interface for market data access.

Concrete implementations: HyperliquidDataAdapter, BacktestDataAdapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from src.domain.models import Candle, FundingPayment


class MarketDataPort(ABC):
    """Abstract interface for market data.

    Defines the contract all market data adapters must satisfy. Covers
    candle history, order book, funding rates, and exchange metadata.
    """

    @abstractmethod
    def get_candles(
        self,
        coin: str,
        interval: str,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> list[Candle]:
        """Get historical OHLCV candles.

        Args:
            coin: The asset symbol, e.g. ``"BTC"``.
            interval: Candle interval string, e.g. ``"1h"``, ``"15m"``.
            start_time: UTC start of the requested range (inclusive).
            end_time: UTC end of the requested range (exclusive). If
                ``None``, returns data up to the current time.

        Returns:
            List of ``Candle`` objects sorted by timestamp ascending.

        """
        ...

    @abstractmethod
    def get_current_price(self, coin: str) -> Decimal:
        """Get current mid price for a coin."""
        ...

    @abstractmethod
    def get_l2_snapshot(self, coin: str, depth: int = 20) -> dict:
        """Get L2 order book snapshot.

        Returns:
            Dict with ``"bids"`` and ``"asks"`` keys, each a list of
            ``[price, size]`` pairs.

        """
        ...

    @abstractmethod
    def get_funding_history(
        self,
        coin: str,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> list[FundingPayment]:
        """Get historical funding rate payments for a coin."""
        ...

    @abstractmethod
    def get_funding_rate(self, coin: str) -> Decimal:
        """Get the current 8-hour funding rate for a coin.

        Returns:
            Positive means longs pay shorts; negative means shorts pay longs.

        """
        ...

    @abstractmethod
    def get_open_interest(self, coin: str) -> Decimal:
        """Get current open interest for a coin."""
        ...

    @abstractmethod
    def get_all_mids(self) -> dict[str, Decimal]:
        """Get mid prices for all available coins in a single call.

        Critical for cross-sectional operations (short basket ranking,
        correlation monitoring) without O(N) rate limit consumption.
        """
        ...

    @abstractmethod
    def get_meta(self) -> dict:
        """Get exchange metadata including available assets and leverage limits."""
        ...

    @abstractmethod
    def get_recent_trades(self, coin: str, limit: int = 100) -> list[dict]:
        """Get recent public trades for a coin."""
        ...

    @abstractmethod
    def get_oracle_price(self, coin: str) -> Decimal:
        """Get the oracle (index) price for a coin.

        The oracle price is distinct from the mark price. It is the
        external reference used for funding rate calculations and
        liquidation triggers.
        """
        ...

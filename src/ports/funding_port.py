"""Funding port — abstract interface for funding rate operations.

Concrete implementations: HyperliquidFundingAdapter, BacktestFundingAdapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from src.domain.models import FundingPayment


class FundingPort(ABC):
    """Abstract interface for funding rate data and user funding history.

    Separated from MarketDataPort to allow independent adapter composition
    and testing of funding-sensitive strategies.
    """

    @abstractmethod
    def get_funding_rate(self, coin: str) -> Decimal:
        """Get the current 8-hour funding rate for a coin.

        Returns:
            Positive means longs pay shorts; negative means shorts pay longs.
            Per-asset rates vary significantly: BTC ~0.0006%/8h (positive,
            longs pay), PAXG ~-0.0016%/8h (negative, longs receive income).

        """
        ...

    @abstractmethod
    def get_predicted_funding_rate(self, coin: str) -> Decimal:
        """Get the predicted funding rate for the next settlement period.

        Based on the exchange's real-time premium index. Distinct from
        the current settled rate.
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
    def get_user_funding(
        self,
        address: str,
        start_time: datetime,
    ) -> list[FundingPayment]:
        """Get funding payments actually received or paid by a user.

        Unlike ``get_funding_history`` (market-level rates), this returns
        the user's realised funding cashflows including position size
        weighting and sign.
        """
        ...

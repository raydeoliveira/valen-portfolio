"""Risk port — abstract interface for margin and liquidation checks.

Concrete implementations: HyperliquidRiskAdapter, BacktestRiskAdapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal


class RiskPort(ABC):
    """Abstract interface for account-level risk and margin queries.

    Provides pre-trade and post-trade risk primitives. Consumers (strategies,
    order routers) use this port to gate order submission without coupling to
    exchange-specific margin math.
    """

    @abstractmethod
    def check_margin_sufficient(
        self,
        coin: str,
        additional_size: Decimal,
        leverage: float,
    ) -> bool:
        """Check whether free margin covers an additional position.

        This is a pre-trade check. It does not reserve margin.
        """
        ...

    @abstractmethod
    def get_liquidation_price(self, coin: str) -> Decimal | None:
        """Get the liquidation price for the current open position.

        Returns:
            Liquidation price, or ``None`` if there is no open position.

        """
        ...

    @abstractmethod
    def get_max_position_size(self, coin: str, leverage: float) -> Decimal:
        """Get the maximum position size given current free margin.

        Returns ``Decimal("0")`` if no margin is available.
        """
        ...

    @abstractmethod
    def get_portfolio_margin_ratio(self) -> Decimal:
        """Get the account-level margin health ratio.

        Defined as ``used_margin / total_equity``. Approaching 1.0
        indicates the account is near liquidation.
        """
        ...

"""Execution port — abstract interface for order execution.

Concrete implementations: HyperliquidAdapter, BacktestExecutionAdapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from src.domain.models import (
    AccountState,
    OrderRequest,
    Position,
)


class ExecutionPort(ABC):
    """Abstract interface for order execution.

    Defines the contract all execution adapters must satisfy. Covers single
    and batch order operations, position queries, and safety controls.
    """

    @abstractmethod
    def place_order(self, order: OrderRequest) -> str:
        """Place a single order.

        Args:
            order: The order request describing coin, side, size, type, etc.

        Returns:
            Exchange-assigned order ID string.

        """
        ...

    @abstractmethod
    def cancel_order(self, coin: str, order_id: str) -> bool:
        """Cancel a single open order.

        Args:
            coin: The asset symbol, e.g. ``"BTC"``.
            order_id: Exchange-assigned order ID to cancel.

        Returns:
            ``True`` if the cancellation was acknowledged by the exchange.

        """
        ...

    @abstractmethod
    def get_position(self, coin: str) -> Position | None:
        """Get current open position for a single coin.

        Returns:
            ``Position`` if a position is open, ``None`` if flat.

        """
        ...

    @abstractmethod
    def get_account_state(self) -> AccountState:
        """Get current account-level state (margin, equity, positions)."""
        ...

    @abstractmethod
    def update_leverage(
        self, coin: str, leverage: float, is_cross: bool = True
    ) -> bool:
        """Update leverage setting for a coin.

        On Hyperliquid, this operation has ZERO trading fees — enabling
        fee-free portfolio rebalancing via leverage adjustment rather than
        position entry/exit.

        Args:
            coin: The asset symbol, e.g. ``"BTC"``.
            leverage: Target leverage multiplier (1-50 depending on asset).
            is_cross: ``True`` for cross-margin, ``False`` for isolated.

        Returns:
            ``True`` if the exchange accepted the leverage change.

        """
        ...

    @abstractmethod
    def get_mark_price(self, coin: str) -> Decimal:
        """Get current mark price for a coin."""
        ...

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    @abstractmethod
    def bulk_place_orders(self, orders: list[OrderRequest]) -> list[str]:
        """Place up to 50 orders in a single batch request.

        The returned list is parallel to ``orders``: ``result[i]`` is the
        order ID for ``orders[i]``.
        """
        ...

    @abstractmethod
    def bulk_cancel_orders(self, cancels: list[tuple[str, str]]) -> list[bool]:
        """Cancel multiple open orders in a single batch request.

        Args:
            cancels: List of ``(coin, order_id)`` tuples.

        Returns:
            List of booleans: ``True`` if cancel was acknowledged.

        """
        ...

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    @abstractmethod
    def get_open_orders(self, coin: str | None = None) -> list[dict]:
        """Get all open (resting) orders."""
        ...

    @abstractmethod
    def get_fills(
        self,
        coin: str | None = None,
        start_time: datetime | None = None,
    ) -> list[dict]:
        """Get historical fill records."""
        ...

    @abstractmethod
    def schedule_cancel(self, timeout_seconds: int) -> bool:
        """Register a dead man's switch that cancels all open orders.

        If the process does not renew the switch within ``timeout_seconds``,
        the exchange will automatically cancel all open orders. Call with
        ``timeout_seconds=0`` to disarm.
        """
        ...

    @abstractmethod
    def get_all_positions(self) -> list[Position]:
        """Get all currently open positions across all coins."""
        ...

    def update_isolated_margin(self, coin: str, amount: float) -> bool:
        """Add or remove margin from an isolated-margin position.

        ZERO fee on Hyperliquid — same as update_leverage.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support update_isolated_margin"
        )

    def modify_order(
        self,
        coin: str,
        order_id: str,
        is_buy: bool,
        new_size: float,
        new_price: float,
        order_type: dict | None = None,
    ) -> str:
        """Modify an existing resting order in-place.

        Preserves time priority in the order book and uses a single API
        call instead of cancel+replace.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support modify_order"
        )

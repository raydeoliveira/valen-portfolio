"""VALEN domain models — pure Python, no exchange dependencies.

These models are exchange-agnostic. The adapters translate between
exchange-specific formats and these domain types.

All models use Pydantic v2 BaseModel for validation, serialization,
and config compatibility.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_serializer

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Direction(str, Enum):
    """Position direction."""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class OrderSide(str, Enum):
    """Order side."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class TimeInForce(str, Enum):
    """Time in force for limit orders."""

    GTC = "gtc"  # Good-til-cancel
    IOC = "ioc"  # Immediate-or-cancel
    ALO = "alo"  # Add-liquidity-only (maker only)


class OrderStatus(str, Enum):
    """Lifecycle state of an order."""

    NEW = "new"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class SignalUrgency(str, Enum):
    """Execution urgency classification for smart order routing."""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class MarginType(str, Enum):
    """Margin mode for a position."""

    CROSS = "cross"
    ISOLATED = "isolated"


class Timeframe(str, Enum):
    """Canonical candle timeframes.

    Values match the interval strings used in the Hyperliquid API.
    """

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


# ---------------------------------------------------------------------------
# Shared model configs
# ---------------------------------------------------------------------------

_FROZEN_CONFIG = ConfigDict(
    frozen=True,
    arbitrary_types_allowed=True,
)

_MUTABLE_CONFIG = ConfigDict(
    frozen=False,
    arbitrary_types_allowed=True,
)


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class Candle(BaseModel):
    """OHLCV candle for a single interval.

    Attributes:
        timestamp: Candle open time (UTC).
        coin: Asset symbol, e.g. "BTC".
        interval: Candle timeframe.
        open: Opening price.
        high: High price.
        low: Low price.
        close: Closing price.
        volume: Volume traded in base asset units.

    """

    model_config = _FROZEN_CONFIG

    timestamp: datetime
    coin: str = ""
    interval: Timeframe = Timeframe.H1
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @field_serializer("open", "high", "low", "close", "volume")
    def _serialize_decimal(self, value: Decimal) -> str:
        return str(value)

    @field_serializer("timestamp")
    def _serialize_dt(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("interval")
    def _serialize_interval(self, value: Timeframe) -> str:
        return value.value


class OrderRequest(BaseModel):
    """Request to place a new order.

    Attributes:
        coin: Asset symbol, e.g. "BTC".
        side: BUY or SELL.
        size: Order size in base asset units.
        order_type: MARKET, LIMIT, STOP_LOSS, or TAKE_PROFIT.
        limit_price: Required for LIMIT orders.
        trigger_price: Required for STOP_LOSS / TAKE_PROFIT orders.
        time_in_force: GTC, IOC, or ALO.
        reduce_only: If True, order only reduces an existing position.
        leverage: Desired leverage multiplier.
        margin_type: CROSS or ISOLATED margin.

    """

    model_config = _FROZEN_CONFIG

    coin: str
    side: OrderSide
    size: Decimal
    order_type: OrderType
    limit_price: Decimal | None = None
    trigger_price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    leverage: float = 1
    margin_type: MarginType = MarginType.CROSS

    @field_serializer("size", "limit_price", "trigger_price")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return str(value) if value is not None else None


class Trade(BaseModel):
    """An exchange fill / trade record.

    Represents a single execution (fill) from the exchange.
    """

    model_config = _FROZEN_CONFIG

    timestamp: datetime
    coin: str
    price: Decimal
    size: Decimal
    side: OrderSide
    trade_id: str = ""
    order_id: str = ""
    fee: Decimal = Decimal("0")
    fee_currency: str = "USDC"

    @field_serializer("price", "size", "fee")
    def _serialize_decimal(self, value: Decimal) -> str:
        return str(value)

    @field_serializer("timestamp")
    def _serialize_dt(self, value: datetime) -> str:
        return value.isoformat()


class L2BookSnapshot(BaseModel):
    """Level-2 order book snapshot at a point in time."""

    model_config = _FROZEN_CONFIG

    timestamp: datetime
    coin: str
    bids: list[tuple[Decimal, Decimal]]
    asks: list[tuple[Decimal, Decimal]]
    depth: int = 20

    @field_serializer("timestamp")
    def _serialize_dt(self, value: datetime) -> str:
        return value.isoformat()

    def bids_json(self) -> str:
        """Serialize bids to a JSON string for SQLite storage."""
        return json.dumps([[str(p), str(s)] for p, s in self.bids])

    def asks_json(self) -> str:
        """Serialize asks to a JSON string for SQLite storage."""
        return json.dumps([[str(p), str(s)] for p, s in self.asks])


class Signal(BaseModel):
    """A trading signal generated by a sleeve strategy.

    Attributes:
        timestamp: Signal generation time (UTC).
        coin: Asset symbol this signal applies to.
        sleeve: Originating sleeve identifier, e.g. "VALEN Sleeve-BTC".
        direction: LONG, SHORT, or FLAT.
        strength: Signal strength in [0.0, 1.0]. 1.0 = maximum conviction.
        reason: Human-readable explanation of why the signal was generated.
        price: Asset price at signal generation time.
        urgency: Execution urgency for smart order routing.

    """

    model_config = _FROZEN_CONFIG

    timestamp: datetime
    coin: str
    sleeve: str
    direction: Direction
    strength: float = 1.0
    reason: str = ""
    price: Decimal | None = None
    urgency: SignalUrgency = SignalUrgency.NORMAL
    meta: dict[str, str] = {}

    @field_serializer("price")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return str(value) if value is not None else None

    @field_serializer("timestamp")
    def _serialize_dt(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("urgency")
    def _serialize_urgency(self, value: SignalUrgency) -> str:
        return value.value


class Position(BaseModel):
    """Current position state snapshot.

    Attributes:
        coin: Asset symbol.
        direction: LONG, SHORT, or FLAT.
        size: Position size in base asset units.
        entry_price: Average entry price.
        mark_price: Current mark price.
        unrealized_pnl: Unrealized PnL in USDC.
        leverage: Current leverage multiplier.
        liquidation_price: Estimated liquidation price (None if flat).
        margin_used: Margin allocated to this position in USDC.
        funding_accumulated: Total funding paid/received (negative = paid).

    """

    model_config = _MUTABLE_CONFIG

    coin: str
    direction: Direction
    size: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    leverage: float
    margin_type: MarginType = MarginType.CROSS
    liquidation_price: Decimal | None = None
    margin_used: Decimal = Decimal("0")
    funding_accumulated: Decimal = Decimal("0")

    @field_serializer(
        "size", "entry_price", "mark_price", "unrealized_pnl",
        "liquidation_price", "margin_used", "funding_accumulated",
    )
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return str(value) if value is not None else None


class FundingPayment(BaseModel):
    """Funding rate payment received or paid on a perpetual position.

    Attributes:
        timestamp: Payment time (UTC).
        coin: Asset symbol.
        rate: 8-hour funding rate (positive = longs pay shorts).
        payment: Actual USDC payment (negative = paid by position holder).
        position_size: Position size at the time of payment.
        oracle_price: Oracle price used for notional calculation.

    """

    model_config = _FROZEN_CONFIG

    timestamp: datetime
    coin: str
    rate: Decimal
    payment: Decimal
    position_size: Decimal
    oracle_price: Decimal | None = None

    @field_serializer("rate", "payment", "position_size", "oracle_price")
    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        return str(value) if value is not None else None

    @field_serializer("timestamp")
    def _serialize_dt(self, value: datetime) -> str:
        return value.isoformat()


class AccountState(BaseModel):
    """Account-level state snapshot.

    Attributes:
        total_value: Total portfolio value in USDC.
        free_margin: Available margin for new positions.
        used_margin: Margin currently allocated to open positions.
        positions: List of open positions.

    """

    model_config = _MUTABLE_CONFIG

    total_value: Decimal
    free_margin: Decimal
    used_margin: Decimal
    positions: list[Position] = []
    timestamp: datetime | None = None

    @field_serializer("total_value", "free_margin", "used_margin")
    def _serialize_decimal(self, value: Decimal) -> str:
        return str(value)

    @field_serializer("timestamp")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

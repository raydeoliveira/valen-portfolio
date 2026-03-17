# VALEN Architecture

## Design Philosophy

VALEN follows **Clean Architecture** (Ports & Adapters), a pattern refined across seven prior system versions (EISEN S1-S7). The core principle: domain logic must never depend on infrastructure. Exchange SDKs, databases, and CLI frameworks are implementation details that live behind abstract interfaces.

This is not architectural purism for its own sake. In algorithmic trading, the ability to swap execution backends (live exchange, paper trading, backtest engine) without touching strategy logic is a safety requirement. A strategy that works differently in backtest vs. live is a strategy you cannot trust.

---

## Layer Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Entry Points                              │
│  CLI scripts, daemon processes, monitoring dashboard          │
├──────────────────────────────────────────────────────────────┤
│                    Services Layer                              │
│  ┌──────────────┬──────────────┬──────────────────────────┐  │
│  │ Strategy      │ Monitor &    │ Portfolio                 │  │
│  │ Router        │ Alerts       │ Allocator                 │  │
│  │ (P1-P8)       │ (6 types)    │ (5 methods)               │  │
│  └──────────────┴──────────────┴──────────────────────────┘  │
│  ┌──────────────┬──────────────┬──────────────────────────┐  │
│  │ Indicators    │ Execution    │ Rate                      │  │
│  │ (EMA, RSI,    │ Manager      │ Limiter                   │  │
│  │  ATR, BB, ..) │              │                           │  │
│  └──────────────┴──────────────┴──────────────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│                   Ports (Abstract Contracts)                   │
│  ExecutionPort │ MarketDataPort │ FundingPort │ RiskPort      │
├──────────────────────────────────────────────────────────────┤
│                   Adapters (Implementations)                  │
│  ┌──────────────┬───────────────┬─────────────────────────┐  │
│  │ Hyperliquid   │ Backtest      │ Paper Trading            │  │
│  │ (Live REST    │ (Simulated    │ (Testnet-enforced        │  │
│  │  + WebSocket)  │  execution)   │  execution)              │  │
│  └──────────────┴───────────────┴─────────────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│                    Domain Models                               │
│  Candle │ Order │ Position │ Signal │ Fill │ FundingPayment   │
│  AccountState │ OrderRequest │ Direction │ OrderType │ TIF    │
└──────────────────────────────────────────────────────────────┘
```

---

## Port Interfaces

The four ports define the complete boundary between VALEN's logic and the outside world. Every exchange interaction — order placement, data retrieval, risk check — passes through one of these interfaces.

### ExecutionPort

Handles all order lifecycle operations.

```python
class ExecutionPort(ABC):
    # Single operations
    def place_order(self, order: OrderRequest) -> str: ...
    def cancel_order(self, coin: str, order_id: str) -> bool: ...

    # Batch operations (up to 50 orders per call)
    def bulk_place_orders(self, orders: list[OrderRequest]) -> list[str]: ...
    def bulk_cancel_orders(self, cancels: list[tuple[str, str]]) -> list[bool]: ...

    # Position & account queries
    def get_position(self, coin: str) -> Position | None: ...
    def get_all_positions(self) -> list[Position]: ...
    def get_account_state(self) -> AccountState: ...
    def get_open_orders(self, coin: str | None = None) -> list[dict]: ...
    def get_fills(self, coin: str | None, start_time: datetime | None) -> list[dict]: ...

    # Configuration
    def update_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> bool: ...
    def get_mark_price(self, coin: str) -> Decimal: ...

    # Safety
    def schedule_cancel(self, timeout_seconds: int) -> bool: ...  # Dead man's switch
```

Design notes:
- `schedule_cancel` implements a dead man's switch. If the process crashes without renewing the timer, all open orders are automatically cancelled by the exchange.
- Batch operations are critical for grid strategies (P3) that manage dozens of resting orders simultaneously.
- `get_all_positions()` exists separately from `get_position()` because portfolio-level operations (allocator, monitor) need the full picture without N+1 queries.

### MarketDataPort

Covers all read-only market data access.

```python
class MarketDataPort(ABC):
    # OHLCV data
    def get_candles(self, coin: str, interval: str, start_time: datetime,
                    end_time: datetime | None = None) -> list[Candle]: ...

    # Prices
    def get_current_price(self, coin: str) -> Decimal: ...
    def get_all_mids(self) -> dict[str, Decimal]: ...
    def get_oracle_price(self, coin: str) -> Decimal: ...
    def get_mark_price(self, coin: str) -> Decimal: ...  # via ExecutionPort in practice

    # Order book
    def get_l2_snapshot(self, coin: str, depth: int = 20) -> dict: ...

    # Funding
    def get_funding_history(self, coin: str, start_time: datetime,
                            end_time: datetime | None = None) -> list[FundingPayment]: ...
    def get_funding_rate(self, coin: str) -> Decimal: ...

    # Market structure
    def get_open_interest(self, coin: str) -> Decimal: ...
    def get_recent_trades(self, coin: str, limit: int = 100) -> list[dict]: ...
    def get_meta(self) -> dict: ...
```

Design notes:
- `get_all_mids()` returns all coin prices in a single call — essential for cross-sectional strategies (P5 momentum) that need to rank the full universe without hitting rate limits.
- Oracle price is separated from mark price because they differ and serve different purposes (funding calculation vs. PnL marking).

### FundingPort

Dedicated port for funding rate operations, separated from MarketDataPort to allow independent composition and testing of funding-heavy strategies (P4 Funding Arb).

```python
class FundingPort(ABC):
    def get_funding_rate(self, coin: str) -> Decimal: ...
    def get_predicted_funding_rate(self, coin: str) -> Decimal: ...
    def get_funding_history(self, coin: str, start_time: datetime,
                            end_time: datetime | None = None) -> list[FundingPayment]: ...
    def get_user_funding(self, address: str, start_time: datetime) -> list[FundingPayment]: ...
```

Design notes:
- `get_predicted_funding_rate` is distinct from the current rate. The prediction is based on the real-time premium index and can differ significantly from the settled rate.
- `get_user_funding` returns realized cashflows (position-size-weighted), not market-level rates. This distinction matters for PnL attribution.

### RiskPort

Pre-trade and portfolio-level risk queries.

```python
class RiskPort(ABC):
    def check_margin_sufficient(self, coin: str, additional_size: Decimal,
                                 leverage: int) -> bool: ...
    def get_liquidation_price(self, coin: str) -> Decimal | None: ...
    def get_max_position_size(self, coin: str, leverage: int) -> Decimal: ...
    def get_portfolio_margin_ratio(self) -> Decimal: ...
```

Design notes:
- `check_margin_sufficient` is a pre-trade gate. Strategies call this before submitting orders. It does not reserve margin.
- `get_portfolio_margin_ratio` returns `used_margin / total_equity`. Approaching 1.0 means the account is near liquidation. The monitor uses this for margin alerts.

---

## Strategy Router Pattern

Each strategy pillar (P1-P8) is a self-contained module that:

1. Receives market data through ports
2. Computes signals using the indicator library
3. Generates `OrderRequest` objects
4. Submits orders through the execution port

The router dispatches candle updates to active pillars based on configuration. Pillars do not communicate with each other directly — capital allocation across pillars is handled by the portfolio allocator at a higher level.

```
Candle Update
    │
    ▼
┌─────────┐     ┌────────────┐
│  Router  │────▶│  P1: BTC   │──▶ OrderRequest
│          │     │  Treasury   │
│          │     ├────────────┤
│          │────▶│  P2: Short │──▶ OrderRequest
│          │     │  Hedge     │
│          │     ├────────────┤
│          │────▶│  P3: Grid  │──▶ [OrderRequest, ...]  (batch)
│          │     │  Perp      │
│          │     ├────────────┤
│          │────▶│  ...       │
└─────────┘     └────────────┘
                      │
                      ▼
              ExecutionPort.place_order()
              or .bulk_place_orders()
```

### Pillar Isolation

Each pillar:
- Has its own configuration (leverage, position limits, indicators, thresholds)
- Manages its own state (current position, pending orders, signal history)
- Has independent kill criteria (max drawdown, loss streak, Sortino floor)
- Can be enabled/disabled without affecting other pillars

This isolation is enforced architecturally, not by convention. A pillar cannot access another pillar's state or configuration.

---

## Backtest Engine Design

The backtest engine implements the same port contracts as the live adapter, meaning strategies run identically in backtest and live modes. The only difference is the data source and execution simulation.

### Event Flow

```
Historical Candles (SQLite or CSV)
    │
    ▼
┌──────────────────┐
│  BacktestEngine   │
│                    │
│  For each candle:  │
│  1. Update prices  │
│  2. Check stops    │──▶ Simulated fills (with slippage model)
│  3. Settle funding │──▶ 8-hour funding payment simulation
│  4. Check liq.     │──▶ Liquidation detection (margin-based)
│  5. Route candle   │──▶ Strategy generates orders
│  6. Execute orders │──▶ Simulated execution (market/limit/ALO)
│  7. Update equity  │
└──────────────────┘
    │
    ▼
BacktestResult
  ├── Equity curve
  ├── Trade log
  ├── Metrics (Sortino, Omega, Calmar, STARR, max DD, ...)
  └── Funding PnL breakdown
```

### Perp-Native Features

Unlike a simple spot backtester, VALEN's engine models:

- **Funding payments**: Simulated every 8 hours based on historical funding rates. Long positions pay (or receive) funding; short positions receive (or pay).
- **Liquidation detection**: Tracks margin ratio per-bar. If mark price crosses the liquidation threshold, the position is force-closed at a penalty.
- **7-tier fee model**: Matches Hyperliquid's volume-based fee schedule. Maker/taker fees decrease with 30-day volume.
- **Leverage and margin**: Tracks notional exposure, required margin, and free margin throughout the simulation.
- **ALO (Add Liquidity Only)**: Grid strategy orders use ALO to guarantee maker fees. The engine rejects ALO orders that would cross the spread.

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────────────┐ │
│  │ HL REST API   │  │ HL WS Feed │  │ S3 Archive (hist.)  │ │
│  └──────┬───────┘  └─────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼─────────────────────┼────────────┘
          │                │                     │
          ▼                ▼                     ▼
    ┌─────────────────────────────────────────────────┐
    │              Rate Limiter                        │
    │  (IP weight budget + per-address budget)         │
    │  Thread-safe, auto-refilling token buckets       │
    └──────────────────────┬──────────────────────────┘
                           │
                           ▼
    ┌─────────────────────────────────────────────────┐
    │              SQLite Database                     │
    │  ┌──────────┬──────────┬──────────┬──────────┐ │
    │  │ Candles   │  Fills   │ Funding  │ Positions│ │
    │  └──────────┴──────────┴──────────┴──────────┘ │
    └──────────────────────┬──────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Backtest  │ │ Strategy │ │ Monitor  │
        │ Engine    │ │ Router   │ │ Dashboard│
        └──────────┘ └──────────┘ └──────────┘
```

### Rate Limiter Design

Hyperliquid enforces two rate limit budgets:
- **IP weight**: Shared across all requests from the same IP
- **Address weight**: Per-wallet request budget

The rate limiter uses thread-safe token buckets with automatic refill. Every adapter method acquires tokens before making an API call. If the budget is exhausted, the call blocks until tokens refill — no request is ever dropped or retried blindly.

---

## Configuration Architecture

All configuration uses Pydantic v2 models with environment variable support:

```
config/
├── system.json          # Global settings (database path, log level, testnet flag)
├── pillars/
│   ├── p1_btc_treasury.json
│   ├── p2_short_hedge.json
│   ├── p3_grid_perp.json
│   └── ...
└── allocator.json       # Portfolio allocator method and weights
```

Configuration is validated at startup. Invalid configs fail fast with clear error messages rather than silently defaulting.

---

## Testing Strategy

Tests are organized by architectural layer:

| Layer | Test Type | Example |
|-------|-----------|---------|
| Domain | Unit tests | Model validation, enum behavior, serialization |
| Ports | Contract tests | Verify port ABCs define expected methods |
| Adapters | Integration tests | HL adapter against testnet (mocked in CI) |
| Services | Unit + integration | Strategy signal generation, indicator math |
| Backtest | Property tests | Equity curve monotonicity under zero-fee conditions |
| System | End-to-end | Full backtest run with all pillars active |

Key testing principle: **strategy tests never touch the network.** All exchange interactions are mocked through the port interfaces. This is why Clean Architecture matters — it makes strategies fully testable in isolation.

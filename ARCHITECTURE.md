# VALEN Architecture

## Design Philosophy

VALEN follows **Clean Architecture** (Ports & Adapters), refined across seven prior system versions (EISEN S1-S7) and continuous development on Hyperliquid. The core principle: domain logic never depends on infrastructure. Exchange SDKs, databases, and CLI frameworks are implementation details behind abstract interfaces.

This is a safety requirement, not architectural purism. The backtest engine and the live adapter implement identical port contracts. If a strategy produces different behavior in backtest vs. live, that is a bug — not "market impact" or "execution slippage."

---

## 3-Layer Architecture

VALEN separates trading logic into three layers with strict invariants that prevent dangerous coupling:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Entry Points                                  │
│  Orchestrator, paper trader, backtest harness, daemon processes      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: SIGNAL GENERATION                                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Per-sleeve dual-EMA crossover + regime gate                    │ │
│  │ 11 independent configurations (BTC, HYPE, SKY, Oil, ...)      │ │
│  │ Direction decisions: 4h+ cadence ONLY                          │ │
│  │ Sub-hourly modulation: adjusts SIZE, never DIRECTION           │ │
│  │ Signal modes: dual_ema | always_long | independent_regime      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│       │  Invariant: Sub-hourly direction changes are BANNED         │
│       ▼  (0% pass rate across 800+ backtest configurations)         │
│                                                                      │
│  Layer 2: EXECUTION OPTIMIZATION                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ SmartOrderRouter with 6 microstructure gates                   │ │
│  │ VPIN · Kyle's Lambda · Vol regime                              │ │
│  │ TFI · Cascade suppression · RSI                                │ │
│  │ Composite score → ALO maker (1.5 bps) or MARKET taker (4.5)  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│       │  Invariant: L2 NEVER overrides L1 direction                 │
│       ▼                                                              │
│                                                                      │
│  Layer 3: EVENT / SIZING                                             │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ UnifiedEventEngine: calendar, cascade, governance, revenue     │ │
│  │ TailRiskOverlay: drawdown-reactive defensive convexity         │ │
│  │ MomentumSizer: trend-alignment boost (BTC, HYPE, RENDER)      │ │
│  │ SmartMoneySizing: contrarian vault-flow modulation             │ │
│  │ VaultConsensusOverlay: smart money conviction filter           │ │
│  │ A1 Manager: asymmetric stops, breakeven, CEM gradual exit     │ │
│  │ Hierarchical stacking: MAX(boosts), MIN(reductions)           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│       │  Invariant: L3 scales size but NEVER flips direction        │
│       ▼                                                              │
│                                                                      │
│  Portfolio Exposure Governor                                         │
│  Correlation monitoring · DD multiplier · HL leverage clamp          │
│  Per-sleeve exposure caps · Live leverage limits (15-min refresh)    │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                    Ports (Abstract Contracts)                         │
│  ExecutionPort · MarketDataPort · FundingPort · RiskPort             │
├─────────────────────────────────────────────────────────────────────┤
│                    Adapters (Implementations)                        │
│  ┌─────────────────┬────────────────┬────────────────────────────┐  │
│  │ Hyperliquid Live │ Paper Trading  │ Backtest Engine             │  │
│  │ (REST + WS)      │ (Testnet)      │ (Simulated execution)      │  │
│  └─────────────────┴────────────────┴────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                    Domain Models (Pydantic v2)                        │
│  Candle · Order · Position · Signal · Fill · FundingPayment          │
│  AccountState · Direction · OrderType · TimeInForce                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Port Interfaces

Four ports define the complete boundary between VALEN's logic and infrastructure.

### ExecutionPort

Handles order lifecycle, position queries, leverage management, and the dead man's switch:

```python
class ExecutionPort(ABC):
    def place_order(self, order: OrderRequest) -> str: ...
    def cancel_order(self, coin: str, order_id: str) -> bool: ...
    def bulk_place_orders(self, orders: list[OrderRequest]) -> list[str]: ...
    def get_position(self, coin: str) -> Position | None: ...
    def get_all_positions(self) -> list[Position]: ...
    def get_account_state(self) -> AccountState: ...
    def update_leverage(self, coin: str, leverage: int, is_cross: bool) -> bool: ...
    def schedule_cancel(self, timeout_seconds: int) -> bool: ...  # Dead man's switch
```

Design note: `update_leverage()` has **zero trading fees** on Hyperliquid. This enables fee-free rebalancing — a structural advantage over traditional exchanges where rebalancing costs taker fees on every adjustment.

### MarketDataPort

Read-only market data access with batch efficiency:

```python
class MarketDataPort(ABC):
    def get_candles(self, coin: str, interval: str, start: datetime, end: datetime) -> list[Candle]: ...
    def get_all_mids(self) -> dict[str, Decimal]: ...    # Single call for full universe
    def get_l2_snapshot(self, coin: str, depth: int) -> dict: ...
    def get_funding_rate(self, coin: str) -> Decimal: ...
    def get_open_interest(self, coin: str) -> Decimal: ...
```

Design note: `get_all_mids()` returns all prices in a single API call — critical for cross-sectional operations (short basket ranking, correlation monitoring) without O(N) rate limit consumption.

### FundingPort & RiskPort

Separated from MarketDataPort to allow independent composition and testing:

```python
class FundingPort(ABC):
    def get_predicted_funding_rate(self, coin: str) -> Decimal: ...
    def get_user_funding(self, address: str, start: datetime) -> list[FundingPayment]: ...

class RiskPort(ABC):
    def check_margin_sufficient(self, coin: str, size: Decimal, leverage: int) -> bool: ...
    def get_liquidation_price(self, coin: str) -> Decimal | None: ...
    def get_portfolio_margin_ratio(self) -> Decimal: ...
```

---

## SmartOrderRouter (Layer 2)

The SOR replaces the naive "always use market orders" approach with microstructure-aware routing:

```
Signal from L1
    │
    ▼
┌──────────────────────────────────────┐
│  6 Microstructure Gates (parallel)   │
│                                      │
│  VPIN ─────────────── 0.25 ──┐       │
│  Kyle's Lambda ─────  0.20 ──┤       │
│  Vol regime ─────────  0.20 ──┤       │
│  TFI ───────────────  0.15 ──┼──▶ Composite  ──▶  < threshold: ALO (maker)
│  Cascade suppression  0.15 ──┤       score          ≥ threshold: MARKET (taker)
│  RSI suppression ──── 0.05 ──┘                      URGENT: bypass → MARKET
└──────────────────────────────────────┘
```

**Why this matters**: At VIP-0 tier, maker fees (1.5 bps) are 3x cheaper than taker fees (4.5 bps). Over a 6-month period with typical trading activity, intelligent routing saves measurable basis points — and in a system optimizing for Sortino, fee savings directly improve the ratio.

The SOR also includes a health monitor (thread-safe routing statistics) and delay enforcement: when gates recommend delay, the SOR returns a sentinel (not a real fill), and the orchestrator retries on the next evaluation cycle.

---

## Hierarchical Sizing (Layer 3)

Position sizing from multiple overlays is combined using a hierarchical rule that prevents dangerous leverage compounding:

```
MomentumSizer:        +20% boost  ─┐
SmartMoneySizing:     +30% boost  ─┤──▶  MAX(+20%, +30%) = +30% boost
VaultConsensus:       +15% boost  ─┘     (not +65% sum)

TailRiskOverlay:      0.7x reduce ─┐
CalendarGate:         0.8x reduce ─┤──▶  MIN(0.7x, 0.8x) = 0.7x reduce
CascadeDetector:      0.9x reduce ─┘     (most cautious wins)

Final sizing = base × (1.0 + 0.30) × 0.7 = base × 0.91
```

This is a deliberate design choice. Four small boosts at +15% each would compound to +74% with multiplicative stacking — producing dangerous leverage that no single overlay intended. The hierarchical rule caps the upside while preserving full defensive benefit.

---

## A1 Asymmetric Trade Management

Each position has an independent lifecycle manager that handles stops, trails, and exits with per-asset ATR-scaled parameters:

```
Position Open
    │
    ├── ATR trailing stop (regime-aware width)
    │   └── Tightens in trending regimes, widens in choppy/sideways
    │
    ├── Breakeven trigger
    │   └── Moves stop to entry after configurable profit threshold
    │
    ├── Time stop
    │   └── Per-asset maximum hold duration to prevent capital lock-up
    │
    └── CEM gradual exit (Conviction Erosion Model)
        └── Smooth position reduction as edge erodes, vs. binary stop-out
```

**Why per-asset**: ATR-scaled stops mean HYPE (high vol) gets wider stops than PAXG (low vol). A fixed 1.5% stop for all assets was tested and rejected — it stopped out high-vol assets prematurely and let low-vol losses run too long.

---

## Short Basket Architecture

### Euphoria-Fade Entry Scoring

The short basket inverts the conventional scoring model: instead of momentum-following, it **fades euphoria**. High momentum, ATH proximity, elevated social sentiment, and funding spikes are bullish crowd indicators that predict reversals.

### 6-Factor Weekly Rescore

The 229-coin Hyperliquid universe is rescored weekly:

1. **Beta to BTC** — higher beta = better short candidate (amplifies bear moves)
2. **Funding rate** — positive funding = crowd long = contrarian short edge
3. **24h volume** — liquidity filter (minimum threshold for executable size)
4. **Realized volatility** — position sizing input (inverse-vol weighting)
5. **BTC correlation** — higher correlation = better hedge effectiveness
6. **L/S ratio** — crowd positioning (contrarian boost when longs dominate)

Output: 30-coin basket, inverse-volatility weighted.

### 3-Tier Loss Management

| Tier | Scope | Mechanism | Frequency |
|------|-------|-----------|-----------|
| T1 | Per-coin | 6-factor score modulates weight continuously | Every evaluation bar |
| T2 | Basket | Rescore universe, replace weakest positions | Weekly |
| T3 | Per-coin | ATR-scaled emergency hard stop | Continuous |

VRULE-019 proved that no single tier suffices. Every rotation strategy tested was liquidated in the 2024-2025 bull market when tested full-cycle. The 3-tier approach provides defense in depth where each tier catches what the others miss.

---

## Data Architecture (3-Tier Isolation)

```
┌─────────────────────────────────────────────────┐
│  COLD TIER (Archive)                             │
│  hl_archive.db: 200M+ rows, ~40 GB              │
│  Purpose: Backtesting ONLY                       │
│  Access: Read-only, busy_timeout=30s, LIMIT      │
├─────────────────────────────────────────────────┤
│  WARM TIER (Daemon DBs)                          │
│  18 databases: candles, OI, funding, L2, etc.    │
│  Purpose: Production signal computation          │
│  Access: Read-write, WAL mode                    │
├─────────────────────────────────────────────────┤
│  HOT TIER (Live API)                             │
│  Hyperliquid REST + WebSocket                    │
│  Purpose: Execution, real-time prices            │
│  Access: Rate-limited (IP weight + address)      │
└─────────────────────────────────────────────────┘
```

**Key rule**: Never propose reading the 38 GB archive in production. Never use warm-tier daemon data for backtesting. The tier boundaries exist because mixing them produces either (a) production latency from archive queries or (b) backtest data snooping from warm-tier leakage.

---

## Configuration Architecture

All configuration uses Pydantic v2 models with environment variable support and validation at startup:

```
config/
├── portfolio_production.json     # Master config (11 sleeves, weights, leverages)
├── sleeve_btc.json               # Per-sleeve: EMA periods, regime gate, modulation
├── sleeve_hype.json
├── sleeve_oil.json
├── sleeve_c_short_basket.json    # Short basket: scoring weights, rotation schedule
├── signal_calibration.json       # Per-asset signal calibration parameters
├── fee_model.json                # Canonical fees (taker 4.5 bps, maker 1.5 bps)
└── ...                           # 100+ config files total
```

**No hardcoded parameters in strategy code.** Every threshold, EMA period, leverage limit, and fee rate comes from configuration. This is enforced by code review and CI, not convention.

---

## Testing Architecture

Tests organized by architectural layer (5,000+ tests in total):

| Layer | Test Type | Example |
|-------|-----------|---------|
| Domain | Unit | Model validation, enum behavior, Decimal precision |
| Ports | Contract | Port ABCs define expected methods |
| Services | Unit + integration | Signal generation, SOR routing, sizing math |
| Backtesting | Property + integration | Fee model accuracy, equity monotonicity under zero-fee |
| Infrastructure | Integration | Adapter behavior, DB access, rate limiting |
| Interface contracts | Boundary | Attribute name verification between components |
| System | End-to-end | Full backtest with all sleeves active |

Key principle: **Interface contract tests verify attribute names match between producer and consumer.** This prevents the silent integration failures (wrong attribute names, caught by bare `except`) that were the #1 bug category discovered during a 15-agent deep audit.

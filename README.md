
```
██╗   ██╗ █████╗ ██╗     ███████╗███╗   ██╗
██║   ██║██╔══██╗██║     ██╔════╝████╗  ██║
██║   ██║███████║██║     █████╗  ██╔██╗ ██║
╚██╗ ██╔╝██╔══██║██║     ██╔══╝  ██║╚██╗██║
 ╚████╔╝ ██║  ██║███████╗███████╗██║ ╚████║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝
```

# VALEN — Algorithmic Trading System for Hyperliquid DEX

**A perp-native, multi-strategy algorithmic trading system built with Clean Architecture, rigorous quantitative methodology, and AI-augmented development.**

> This is a portfolio showcase. The full codebase lives in a private repository.

---

## Highlights

| Metric | Value |
|--------|-------|
| Strategy pillars | **8** (treasury, hedging, grid, funding arb, momentum, mean reversion, liquidation hunting) |
| Automated tests | **497+** (pytest) |
| Issues closed in one sprint | **27** |
| PRs merged in one sprint | **18** |
| Parallel AI agents | **13** coordinated via custom harness |
| Architecture | Clean Architecture — full port/adapter separation |
| Perp-native features | Leverage, funding rates, liquidation modeling, ALO maker orders |

---

## Architecture

VALEN follows Clean Architecture (Ports & Adapters), ensuring the domain logic is completely decoupled from exchange specifics. Every exchange interaction passes through an abstract port, making the system testable, adaptable, and safe.

```
┌─────────────────────────────────────────────┐
│               CLI / Scripts                  │
├─────────────────────────────────────────────┤
│            Services Layer                    │
│  ┌──────────┬───────────┬─────────────────┐ │
│  │  Router   │  Monitor  │   Allocator     │ │
│  │  (P1-P8)  │  + Alerts │   (5 methods)   │ │
│  └──────────┴───────────┴─────────────────┘ │
├─────────────────────────────────────────────┤
│             Ports (ABCs)                     │
│  ExecutionPort  │  MarketDataPort            │
│  FundingPort    │  RiskPort                  │
├─────────────────────────────────────────────┤
│           Adapters Layer                     │
│  ┌───────────────┬─────────────────────┐    │
│  │  Hyperliquid   │   Paper Trading     │    │
│  │  (REST + WS)   │   (Testnet)         │    │
│  └───────────────┴─────────────────────┘    │
├─────────────────────────────────────────────┤
│      Domain Models (Pydantic v2)             │
│  Candle │ Order │ Position │ Signal │ Fill   │
└─────────────────────────────────────────────┘
```

Four abstract ports define the exchange boundary:

- **ExecutionPort** — Order placement (single + batch), cancellation, position queries, leverage management, dead man's switch
- **MarketDataPort** — Candles, L2 book snapshots, funding rates, open interest, oracle prices, exchange metadata
- **FundingPort** — Current and predicted funding rates, historical funding, user-level funding cashflows
- **RiskPort** — Pre-trade margin checks, liquidation price, max position sizing, portfolio margin ratio

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

---

## Strategy Pillars

VALEN runs up to 8 independent strategy pillars, each with its own signal logic, risk parameters, and allocation budget. A portfolio allocator coordinates capital across active pillars.

| Pillar | Name | Approach | Heritage |
|--------|------|----------|----------|
| **P1** | BTC Treasury | Predictive hold, regime-aware EMA crossover | Ported from EISEN V11 |
| **P2** | Short Hedge | Bear-market overlay, multi-signal confirmation | Redesigned — was eliminated on Coinbase |
| **P3** | Grid Perp | Bidirectional grid, maker-only ALO orders | Redesigned — fee structure now viable |
| **P4** | Funding Arb | Delta-neutral funding rate capture | New — Hyperliquid-native |
| **P5** | Multi-Asset Momentum | Cross-sectional long/short baskets | Redesigned with short-side alpha |
| **P6** | Mean Reversion | Whipsaw recovery, session-aware entry | Ported from EISEN P7 |
| **P7** | NLH Perp | New listing hunter with short-side | Planned |
| **P8** | Liquidation Hunter | Cascade front-running via OI analysis | New — Hyperliquid-native |

### Why eliminated strategies were reconsidered

Three pillars (P2, P3, P5) were killed on EISEN (Coinbase) but revived for VALEN. This is not wishful thinking — the structural reasons for failure no longer apply:

- **P2 Short Hedge**: Failed on Coinbase due to futures fee drag and limited short instruments. On Hyperliquid: native perp shorts at 0.025% taker, no separate futures account.
- **P3 Grid**: Failed on Coinbase due to 0.015% taker with no maker rebates. On Hyperliquid: 0.02% maker fee with rebate potential at higher volume tiers.
- **P5 Momentum**: Failed on Coinbase (-38.85% forward test) due to spot-only constraints and fee drag. On Hyperliquid: 100+ perp markets, leverage, and short-side capability.

Each revived pillar carries explicit kill criteria inherited from its EISEN post-mortem.

---

## Infrastructure

### Backtest Engine
- Perp-native: models funding payments, liquidation detection, leverage, and margin
- 7-tier fee model matching Hyperliquid's volume-based fee schedule
- Event-driven candle iteration with configurable slippage
- Funding rate simulation using historical 8-hour settlement data
- Sortino, Omega, Calmar, and STARR ratio computation

### Portfolio Allocator
Five allocation methods, selectable per system state:
- **Equal Weight** — baseline, even split across active pillars
- **Risk Parity** — inverse-volatility weighting
- **Performance Weighted** — Sortino-ranked allocation
- **Kelly** — Kelly criterion sizing with configurable fractional Kelly
- **Fixed** — manual allocation for testing

### Real-Time Monitoring
- Rich CLI dashboard with live position, PnL, and margin data
- 6 alert types: drawdown, margin, funding spike, connection loss, fill confirmation, liquidation proximity
- WebSocket data daemon with auto-reconnection and heartbeat
- Structured logging (no print statements — ever)

### Data Pipeline
- S3 archive downloader for historical candle backfill
- SQLite persistence layer for candles, fills, funding, and positions
- Data quality checks with gap detection and staleness alerts
- Thread-safe rate limiter with IP weight and per-address budget tracking

### Paper Trading
- Full paper trading engine with testnet enforcement
- Position simulation with realistic fill modeling
- Identical interface to live execution (same port contract)

### CI/CD
- GitHub Actions workflow for lint (ruff), type check (mypy), and test (pytest)
- Agent verification pipeline (`agent_verify.sh`)
- Architecture conformance checks (import boundary enforcement)

---

## AI-Augmented Development

This is where VALEN's development process is unusual. The entire system was built using a coordinated swarm of 13 parallel AI agents, managed through a custom harness.

### The Numbers

| Metric | Value |
|--------|-------|
| AI agents (parallel) | 13 |
| Issues closed | 27 |
| PRs merged | 18 |
| Tests written | 497+ |
| Development model | Wave-based parallel execution |
| Agent personas | 9 specialized roles |
| Coordination | Git worktree isolation + GitHub Projects |

### Wave-Based Development

Work was organized into dependency waves. Each wave's issues could be developed in parallel by separate agents:

```
Wave 0 (Foundation)     7 issues    Domain models, SQLite, ports, CI, rate limiter, data pipeline
        │
        ▼
Wave 1 (Core Engine)    4 issues    HL adapter, backtest engine, P6 mean reversion, P4 research
        │
        ▼
Wave 1.5 (Strategies)   2 issues    P2 short hedge, monitoring dashboard
        │
        ▼
Wave 2 (Strategies)     2 issues    P1 BTC treasury, P3 grid perp
        │
        ▼
Wave 3 (Final)          4 issues    Paper trading, P5 momentum, allocator, P8 research
```

### Agent Coordination Protocol

- **Git worktree isolation**: Each agent works in its own worktree, preventing file conflicts
- **Branch naming**: `<type>/<pillar>/<description>` (e.g., `feat/p2/short-hedge-strategy`)
- **Agent-ID tracking**: Every commit includes the agent's identity for auditability
- **Tiered assignment**: Opus-tier agents for critical path (strategies, backtest engine); Sonnet-tier for infrastructure (CI, data pipeline, monitoring)
- **Conflict resolution**: Defined protocol for when parallel work touches shared files (ports, domain models)
- **Verification gate**: Every PR must pass `agent_verify.sh` before merge

### Agent Personas

Nine specialized personas, each with domain expertise:

| Persona | Role | Example Assignment |
|---------|------|--------------------|
| Quant Architect | System design, port interfaces | Domain models, ports |
| Strategy Engineer | Signal logic, indicator implementation | P1, P2, P3, P6 strategies |
| Infrastructure Engineer | Data pipeline, adapters | HL adapter, SQLite, rate limiter |
| Risk Engineer | Margin modeling, kill criteria | Backtest engine, risk port |
| Research Analyst | Hypothesis formulation, dead-end analysis | P4 funding arb research, P8 liquidation research |
| DeFi Specialist | On-chain mechanics, funding rates | Hyperliquid-specific features |
| Test Engineer | Test design, coverage | 497+ test functions |
| DevOps Engineer | CI/CD, deployment | GitHub Actions, verification |
| Coordinator | Wave planning, conflict resolution | Issue triage, agent assignment |

See [AI_DEVELOPMENT.md](AI_DEVELOPMENT.md) for the full deep dive.

---

## Optimization Philosophy

VALEN uses crypto-appropriate optimization targets. This is a deliberate choice, not a default.

| Priority | Metric | Rationale |
|----------|--------|-----------|
| Primary | **Sortino (gamma=2)** | Penalizes only downside volatility. Upside vol is desirable in crypto. |
| Secondary | **Omega (threshold=0)** | Full-distribution, probability-weighted gain/loss ratio. |
| Tertiary | **Calmar** | Return / max drawdown — the metric that keeps you alive. |
| Leverage-aware | **STARR** | Sortino-to-Average-Realized-Risk for leverage-adjusted performance. |
| **Never** | **Sharpe** | Penalizes upside volatility, which is structurally wrong for right-skewed crypto returns. |

### Why Not Sharpe?

The Sharpe ratio treats upside and downside volatility identically. In crypto, a strategy that captures 40% upside moves while limiting drawdowns to 8% has high total volatility but excellent risk-adjusted returns. Sharpe penalizes it. Sortino rewards it. This is not academic — it changes which parameter sets survive optimization.

---

## Engineering Standards

- **Clean Architecture**: Domain models have zero exchange dependencies. Ports define contracts. Adapters implement them.
- **Pydantic v2**: All domain models are validated, serializable, and config-compatible.
- **Type safety**: Full type hints, mypy strict mode.
- **Linting**: ruff with a comprehensive rule set.
- **Testing**: 497+ test functions covering domain logic, port contracts, adapter behavior, strategy signal generation, backtest mechanics, and integration scenarios.
- **Logging**: Structured logging via `src.services.logger`. No `print()` calls anywhere in the codebase.
- **Verification**: `agent_verify.sh` runs lint, type check, tests, and architecture conformance in a single pass.

See [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) for the full standards document.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11 |
| Models | Pydantic v2 |
| Data | pandas, numpy, scipy |
| Exchange SDK | hyperliquid-python-sdk |
| Database | SQLite |
| CLI | Rich |
| Testing | pytest, pytest-mock |
| Linting | ruff, mypy |
| CI/CD | GitHub Actions |

---

## Project Structure

```
├── src/
│   ├── domain/            # Pydantic v2 models (Candle, Order, Position, Signal, ...)
│   ├── ports/             # Abstract interfaces (ExecutionPort, MarketDataPort, FundingPort, RiskPort)
│   ├── adapters/          # Hyperliquid SDK wrapper (REST + WebSocket)
│   ├── services/
│   │   ├── router/        # Strategy pillars (P1-P8)
│   │   ├── indicators/    # Technical indicators (EMA, RSI, ATR, Bollinger, ROC, Momentum)
│   │   ├── monitor.py     # Real-time monitoring dashboard
│   │   ├── alerts.py      # Alert engine (6 alert types)
│   │   ├── portfolio_allocator.py  # 5 allocation methods
│   │   └── rate_limiter.py         # Thread-safe HL rate limiter
│   ├── backtesting/       # Perp-native backtest engine
│   ├── data/              # SQLite persistence layer
│   └── config_mod/        # Pydantic-based settings
├── config/                # Strategy & system configuration
├── scripts/               # CLI tools, data pipeline, verification
├── tests/                 # 497+ pytest tests
├── research/              # Hypothesis registry & campaign results
├── .harness/              # AI agent coordination (personas, skills, workflows, hooks)
└── .github/               # CI/CD workflows & agent protocol (AGENTS.md)
```

---

## Relationship to EISEN

VALEN is the successor to [EISEN](https://github.com/raydeoliveira), a similar algorithmic trading system built for Coinbase Advanced Trade. EISEN reached version S7 with 4 active pillars before hitting structural ceilings imposed by Coinbase's fee model and instrument limitations.

Key insight: **strategies that were rigorously eliminated on Coinbase deserve re-evaluation on Hyperliquid.** The failure mode matters. If a strategy failed due to exchange-specific constraints (fee drag, no native shorts, no maker rebates) rather than fundamental alpha decay, it becomes a candidate when those constraints are removed.

VALEN carries forward:
- Clean Architecture patterns (refined over 7 system versions)
- Hypothesis-driven development methodology
- Optimization target selection (Sortino > Sharpe)
- 9 meta-patterns distilled from EISEN's research history
- Dead-end classifications that prevent repeating past mistakes

VALEN does NOT carry forward:
- Coinbase-specific adapters or API logic
- Parameter values (re-optimized for HL's fee/funding environment)
- Spot-only assumptions

---

## Methodology

The research process follows a formal hypothesis-driven framework:

1. **Hypothesis** — Falsifiable statement with measurable prediction
2. **Test Plan** — Dataset, timeframe, metrics, statistical tests
3. **Kill Criteria** — Pre-defined thresholds that trigger elimination
4. **Execution** — Backtest campaign with factorial parameter sweep
5. **Temporal Red-Team** — Challenge results with regime analysis, lookahead bias check, data snooping audit
6. **Verdict** — Accept, reject, or modify with evidence

See [METHODOLOGY.md](METHODOLOGY.md) for the full research framework.

---

## Benchmarks

| Benchmark | Purpose |
|-----------|---------|
| Growi HF Vault | Primary — professional HF vault on Hyperliquid |
| BTC buy-and-hold | Secondary — passive baseline |
| EISEN S7 | Tertiary — predecessor system performance |

---

*This is a portfolio showcase repository. The full codebase, backtest results, and live trading infrastructure are maintained in a private repository.*

*Built by [Ray De Oliveira](https://github.com/raydeoliveira)*

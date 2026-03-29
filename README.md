
```
██╗   ██╗ █████╗ ██╗     ███████╗███╗   ██╗
██║   ██║██╔══██╗██║     ██╔════╝████╗  ██║
██║   ██║███████║██║     █████╗  ██╔██╗ ██║
╚██╗ ██╔╝██╔══██║██║     ██╔══╝  ██║╚██╗██║
 ╚████╔╝ ██║  ██║███████╗███████╗██║ ╚████║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝
```

# VALEN — Multi-Asset Algorithmic Trading System

**A 3-layer, 11-sleeve algorithmic trading system for Hyperliquid DEX perpetual futures. Built with Clean Architecture, rigorous quantitative research (900+ backtests, 81 hypotheses), and AI-augmented development at scale (763+ PRs, 4,500+ tests).**

> This is a portfolio showcase. The full codebase lives in a private repository.

### What This Demonstrates

- **Systems architecture**: 3-layer separation with strict invariants, Clean Architecture with CI-enforced import boundaries
- **Quantitative rigor**: 900+ backtests, 81 hypotheses with formal kill criteria, 21 documented dead-ends (VRULEs)
- **Risk engineering**: Asymmetric short-book risk bounded by 3-tier defense-in-depth; hierarchical sizing prevents leverage compounding
- **Data engineering**: 28 collection daemons, 208M+ row archive, 18 SQLite databases with 3-tier isolation (cold/warm/hot)
- **Process engineering**: 53-rule agent contract evolved from production incidents, each rule traceable to a specific bug
- **Execution optimization**: Microstructure-aware order routing (6 gates, maker/taker decision) saving measurable basis points
- **Intellectual honesty**: Strategies that were tested and rejected are documented with equal rigor to those that survived

---

## System at a Glance

| Dimension | Detail |
|-----------|--------|
| Architecture | 3-layer (Signal → Execution → Event/Sizing), 11 independent sleeves |
| Tests | **4,542** across 257 test files |
| PRs merged | **763+** across 6 months of continuous development |
| Research rigor | **81 hypotheses** tested, **21 dead-end verdicts** (VRULEs), **900+ backtests** |
| Data infrastructure | 28 collection daemons, 208M+ rows, 18 SQLite databases |
| Optimization | Sortino(gamma=2) primary — Sharpe is structurally wrong for crypto |
| AI development | Multi-agent parallel development with git worktree isolation |

---

## Why This System Exists

Most algorithmic trading systems are either (a) simple momentum/mean-reversion strategies that work in backtests but fail live, or (b) black-box ML systems that overfit to historical patterns.

VALEN takes a different approach: **hypothesis-driven architecture where every component has survived rigorous elimination testing.** The system is defined as much by what was tested and rejected (21 VRULEs) as by what survived. Funding arbitrage, sub-hourly directional trading, dynamic leverage allocation, strategy-mode switching — all tested with statistical rigor, all rejected with documented evidence.

What remains is a system built on components that have been adversarially challenged across multiple market regimes, fee models, and asset classes.

---

## Architecture

### 3-Layer Design

The system separates concerns into three layers with strict invariants:

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: SIGNAL                                                │
│  Per-sleeve dual-EMA crossover + regime gate                    │
│  Direction decisions at 4h+ cadence only                        │
│  11 independent sleeve configurations                           │
│  Key invariant: Sub-hourly direction changes are BANNED          │
│  (0% pass rate across 800+ tests — fee drag exceeds alpha)      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: EXECUTION                                              │
│  SmartOrderRouter with 6 microstructure gates                    │
│  VPIN (toxicity) · Kyle's Lambda (impact) · Vol regime           │
│  TFI (adverse selection) · Cascade suppression · RSI             │
│  Routes: ALO maker (1.5 bps) vs MARKET taker (4.5 bps)         │
│  Key invariant: L2 NEVER overrides L1 direction                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: EVENT / SIZING                                        │
│  UnifiedEventEngine + TailRiskOverlay + MomentumSizer           │
│  SmartMoneySizing + VaultConsensusOverlay                        │
│  Hierarchical stacking: MAX(boosts), MIN(reductions)            │
│  Key invariant: L3 scales size but NEVER flips direction        │
└─────────────────────────────────────────────────────────────────┘
```

### 11-Sleeve Portfolio

**Long Book** (10 sleeves):

| Sleeve | Asset | Signal Mode | Why Included |
|--------|-------|------------|--------------|
| BTC | BTC | Dual-EMA + regime gate | Core crypto exposure, deepest liquidity |
| HYPE | HYPE | Dual-EMA + regime gate | Hyperliquid native token, exchange-aligned |
| SKY | SKY | Dual-EMA | DeFi governance revenue (MakerDAO successor) |
| Oil | xyz:CL | Independent regime | Crypto-decorrelated (corr -0.177 to BTC) |
| AZTEC | AZTEC | Dual-EMA | Privacy infrastructure, high-conviction thesis |
| PAXG | PAXG | Always-long | Gold-backed safe haven, negative funding = income |
| RENDER | RENDER | Dual-EMA | GPU compute demand proxy |
| NVDA | km:NVDA | Dual-EMA | TradFi AI exposure via institutional perps |
| TSLA | km:TSLA | Dual-EMA | TradFi volatility, negative funding |
| PLTR | km:PLTR | Dual-EMA | TradFi defense/AI, negative funding |

**Hedge Book** (1 sleeve): 25-coin inverse-volatility-weighted short basket with euphoria-fade scoring and 3-tier loss management (per-coin factor modulation → weekly basket rotation → ATR hard stops).

### Clean Architecture (Ports & Adapters)

```
Domain Models (Pydantic v2)     ← Zero exchange dependencies
    ▲
Ports (Abstract contracts)      ← ExecutionPort, MarketDataPort, FundingPort, RiskPort
    ▲
Services Layer                  ← Signal engines, SOR, sizing overlays, governor
    ▲
Adapters                        ← Hyperliquid SDK, paper trading, backtest engine
```

The backtest engine and the live trading adapter implement identical port contracts. A strategy that produces different behavior in backtest vs. live is a strategy with a bug, not a strategy with "market impact."

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete design.

---

## Research Methodology

### Evidence-Driven Elimination

The system's credibility comes from what it has rigorously killed, not just what it runs:

| Dead-End Verdict | Finding | Evidence |
|------------------|---------|----------|
| VRULE-001 | Dynamic leverage per regime is dead | Multi-asset, multi-window testing |
| VRULE-012 | Strategy-mode engines lose to dual-EMA | Factorial comparison across all sleeves |
| VRULE-013 | Cross-exchange derivatives data: zero alpha for BTC | Coinalyze OI/funding, 331K hourly obs |
| VRULE-019 | Naked shorts LIQUIDATED in bull markets | Full-cycle backtest incl. 2024-25 bull |
| VRULE-020 | Funding drag is per-asset, not uniform | Original 0.01%/8h was 16x overstated for BTC |
| VRULE-021 | Mean reversion during sideways loses to holding | Regime-switching fails at transitions |

### The Strongest Meta-Finding

**Per-asset signal decomposition improved Portfolio Sortino by +123%.** Every signal, threshold, modulation frequency, and stop width performs better when calibrated per-asset rather than using aggregate portfolio-level values. This finding — discovered through systematic factorial testing across 6 accepted component improvements — changed the entire system design philosophy.

### Hypothesis-Driven Development

Every proposed change follows a formal lifecycle: Hypothesis → Test Plan → Kill Criteria → Factorial Campaign → Temporal Red-Team → Verdict. All 81 hypotheses are tracked in a central registry with unique IDs, parent hypotheses, test results, and verdict rationale.

See [METHODOLOGY.md](METHODOLOGY.md) for the full research framework.

---

## Execution Layer

### SmartOrderRouter

The SOR evaluates 6 microstructure gates and computes a weighted composite score to decide between maker (ALO, ~1.5 bps) and taker (MARKET, ~4.5 bps) routing:

| Gate | Weight | What It Detects |
|------|--------|----------------|
| VPIN (Volume-Synchronized PIN) | 0.25 | Informed flow / toxicity |
| Kyle's Lambda | 0.20 | Expected price impact |
| Volatility regime | 0.20 | Regime-appropriate urgency |
| Trade Flow Imbalance | 0.15 | Adverse selection risk |
| Cascade suppression | 0.15 | Liquidation cascade detection |
| RSI suppression | 0.05 | Short-term overbought/oversold |

### Hierarchical Sizing (Option C)

Position sizing overlays stack via a hierarchical rule that prevents dangerous leverage compounding:

- **Boosts**: Take MAX of all confirmation boosts (not sum)
- **Reductions**: Take MIN of all reduction factors (most cautious wins)

Four independent sizing signals overlap: momentum alignment, smart money positioning, calendar event gates, and tail risk drawdown scaling. The hierarchical rule ensures they never compound into excessive leverage.

---

## Risk Engineering

### Short Basket: 3-Tier Loss Management

Short positions face asymmetric risk (unlimited upside exposure). VALEN bounds short-book losses through three independent tiers:

| Tier | Mechanism | Frequency |
|------|-----------|-----------|
| T1: Per-coin factor modulation | 6-factor score adjusts weight continuously | Every bar |
| T2: Weekly basket rotation | Rescore 229-coin universe, replace weakest 10 | Weekly |
| T3: ATR hard stops | Emergency per-position stop-loss | Continuous |

**Key insight**: No single tier is sufficient. VRULE-019 showed that even sophisticated rotation strategies get liquidated in sustained bull markets. The 3-tier approach provides defense in depth.

### Euphoria-Fade Short Entry

The short basket uses inverted scoring: high momentum, ATH proximity, elevated social sentiment, and funding spikes are all *bullish crowd indicators* that predict reversals. This produces better short timing than momentum-following because shorts profit from reversals, not continuations.

### Portfolio Exposure Governor

Real-time portfolio-level risk management:
- Cross-asset correlation monitoring (high correlation = reduce exposure)
- Drawdown-reactive position scaling
- Hyperliquid leverage limit enforcement (live API, 15-min refresh)
- Per-sleeve exposure caps

---

## Infrastructure

### Data Pipeline (28 Daemons)

| Category | Daemons | Data |
|----------|---------|------|
| Candle collection | 6 | 4h, 1h, 15m candles for 229+ coins |
| L2 order book | 2 | Bid/ask snapshots for microstructure gates |
| Funding rates | 2 | Per-asset funding (positive AND negative) |
| Open interest | 2 | OI snapshots for cascade detection |
| Vault flows | 3 | Smart money deposit/withdrawal tracking |
| Governance/revenue | 2 | SKY protocol revenue, governance events |
| Social/sentiment | 3 | Galaxy scores, LunarCrush data |
| Archive maintenance | 4 | WAL checkpoints, integrity validation |
| Misc | 4 | Token unlocks, liquidation feeds, health monitors |

**208M+ rows** in the primary archive (38 GB SQLite, WAL mode). 18 total databases with strict tier separation: cold (archive, backtesting only) / warm (daemon DBs, production signals) / hot (live API, execution).

### Fee Model

All backtests use a canonical fee model reflecting VIP-0 tiers: 4.5 bps taker, 1.5 bps maker. The model correctly handles:
- Zero-fee leverage changes via `update_leverage` / `updateIsolatedMargin`
- Per-asset funding rates (BTC ~0.0006%/8h positive; PAXG ~-0.0016%/8h negative = income)
- ALO maker-only routing from the SmartOrderRouter

---

## AI-Augmented Development

### Scale

| Metric | Value |
|--------|-------|
| PRs merged | **763+** |
| Tests | **4,542** across 257 files |
| Agent contract rules | **53** (evolved from 10 initial rules) |
| Research verdicts (VRULEs) | **21** |
| Total commits | **1,200+** |
| Development period | 6 months continuous |

### Multi-Agent Coordination

Development uses parallel AI agents with:
- **Git worktree isolation**: Each agent works in its own worktree
- **Conflict preflight**: Mandatory `conflict_preflight.sh` before picking up work
- **Merge orchestrator**: Computes safe PR merge ordering
- **53-rule agent contract**: Evolved through production incidents (rules 44-53 added after a deep audit found 53 bugs)
- **Verification gate**: `agent_verify.sh` runs lint + type check + tests + architecture conformance

### How Rules Evolved

The agent contract started with 10 basic rules. Each production incident or research failure added specific rules to prevent recurrence:

- **Rules 29-38**: Prevent the specific failure modes discovered during S3.0-S3.2 research (claiming system-level results from component tests, premature VRULEs, missing factorial interaction testing)
- **Rules 44-53**: Added after a 15-agent deep audit found 53 bugs including dead code, silent exception swallowing, interface mismatches, and state persistence failures

See [AI_DEVELOPMENT.md](AI_DEVELOPMENT.md) for the full deep dive.

---

## Engineering Standards

- **Clean Architecture**: Domain models have zero exchange dependencies. Import boundaries enforced by CI.
- **Pydantic v2**: All domain models validated, serializable. `Decimal` for all financial values.
- **Type safety**: Full type hints, mypy strict mode.
- **Canonical fee model**: Single source of truth for fees. Hardcoded rates in ad-hoc scripts are banned.
- **Interface contract tests**: Every component boundary has explicit attribute verification tests.
- **No silent exception swallowing**: `except Exception: pass` is banned (Rule 45). Every handler logs or re-raises.
- **State persistence round-trip tests**: Every `save_state()` field verified in `load_state()` (Rule 52).
- **Dead code audit per PR**: Every new method must be called from production code (Rule 50).

See [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) for the full standards document.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Models | Pydantic v2 |
| Data | pandas, numpy, scipy |
| Exchange SDK | hyperliquid-python-sdk |
| Database | SQLite (WAL mode, 18 databases) |
| Testing | pytest (4,542 tests) |
| Linting | ruff, mypy --strict |
| CI/CD | GitHub Actions |
| Deployment | launchd daemons (28), ChartVPS |

---

## Relationship to EISEN

VALEN is the successor to [EISEN](https://github.com/raydeoliveira/eisen-portfolio), a similar system built for Coinbase Advanced Trade. EISEN reached S7 with 4 active pillars before hitting structural ceilings.

**What transferred**: Clean Architecture patterns (refined over 7 versions), hypothesis-driven methodology, 9 meta-patterns, optimization target selection (Sortino over Sharpe), dead-end documentation practice.

**What was re-evaluated and rejected again**: Funding arbitrage (no alpha at any frequency), mean reversion (loses to holding in sideways), grid trading (viable but dominated by directional). The intellectual honesty to re-test and re-reject was as important as the new findings.

**What was re-evaluated and accepted**: Short hedging (native perp shorts at lower fees), multi-asset momentum (100+ perp markets with short-side), per-asset signal decomposition (strongest meta-finding, +123% Sortino improvement).

---

*This is a portfolio showcase repository. The full codebase, backtest results, and live trading infrastructure are maintained in a private repository.*

*Built by [Ray De Oliveira](https://github.com/raydeoliveira)*

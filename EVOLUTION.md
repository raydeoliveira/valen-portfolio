# System Evolution

VALEN has gone through four major system versions, each representing a fundamental shift in architecture, capability, or operational status. This document traces the arc from initial prototype to live production system.

---

## S1 — Foundation (Early Development)

**Goal**: Prove that Clean Architecture + hypothesis-driven development could produce a viable Hyperliquid trading system.

**Architecture**: Single-asset (BTC-only), single-layer signal pipeline, basic execution.

**Key decisions**:
- Chose Hyperliquid DEX over centralized exchanges for perp-native design, zero-fee leverage changes, and deep liquidity
- Adopted Clean Architecture (Ports & Adapters) — validated across 7 EISEN versions
- Sortino(gamma=2) as primary optimization target (never Sharpe — penalizes desirable upside volatility)
- Hypothesis-driven development: every parameter justified by a formal test with kill criteria

**What was built**:
- Domain models (Pydantic v2, `Decimal` for all financial values, frozen immutability)
- 4 port interfaces (Execution, MarketData, Funding, Risk)
- Hyperliquid adapter (REST + WebSocket)
- Backtest engine implementing identical port contracts to live adapter
- Initial signal pipeline: dual-EMA crossover
- Canonical fee model (single source of truth for VIP-0 tiers)

**What was learned**:
- Sub-hourly directional signals have 0% pass rate across 800+ configurations — fee drag exceeds alpha at VIP-0
- The 4h cadence constraint became a foundational invariant that shaped all future architecture

**Metrics**: ~500 tests, ~50 backtests, 10 agent contract rules

---

## S2 — Multi-Asset Expansion

**Goal**: Expand beyond BTC to a diversified multi-sleeve portfolio with a short hedge.

**Architecture**: Multi-asset (11 sleeves), 2-layer (Signal + Execution), initial short basket.

**Key decisions**:
- Per-sleeve independence: each sleeve has its own signal config, not a shared global template
- Added TradFi instruments via builder perps (km: prefix — NVDA, RTX, PLTR) for cross-asset decorrelation
- Commodity exposure (Oil via xyz:CL) for crypto-decorrelated returns (corr -0.177 to BTC)
- Short basket with inverse-volatility weighting for portfolio-level hedge

**What was built**:
- 10 long sleeves + 1 short basket sleeve
- Per-sleeve configuration system (109 config files)
- SmartOrderRouter with 6 microstructure gates (VPIN, Kyle's Lambda, Vol regime, TFI, Cascade, RSI)
- Short basket engine with euphoria-fade scoring and weekly 6-factor rescore across 229-coin universe
- Data collection pipeline (28 daemons: candles, L2, funding, OI, vault flows, sentiment)
- SQLite archive: 208M+ rows, 38 GB, 3-tier isolation (cold/warm/hot)

**What was learned**:
- **Per-asset signal decomposition improved Sortino by +123%** — the single strongest meta-finding. Aggregate signals are almost always inferior to per-asset calibration.
- Naked shorts get liquidated in bull markets (VRULE-019) — 3-tier loss management is mandatory
- Dynamic leverage per regime is dead (VRULE-001) — static allocations with stress-based modulation outperform
- Strategy-mode engines lose to dual-EMA (VRULE-012) — complexity does not reliably beat simplicity
- Funding drag is per-asset, not uniform (VRULE-020) — original 0.01%/8h assumption was 16x wrong for BTC

**Metrics**: ~2,500 tests, ~500 backtests, 43 agent contract rules, 81 hypotheses tracked

---

## S3.x — Research Hardening

**Goal**: Stress-test every component through factorial campaigns, temporal red-teaming, and adversarial audit. Prepare for live deployment.

**Architecture**: 3-layer (Signal → Execution → Event/Sizing), 11 sleeves, hierarchical sizing, automated recalibration.

**Key decisions**:
- Added Layer 3 (Event/Sizing) — sizing overlays were coupling with signal logic and needed separation
- Hierarchical sizing (Option C): MAX(boosts), MIN(reductions) to prevent leverage compounding
- Factorial interaction testing before any multi-component deployment (Rule 31)
- Adversarial VRULE review (Rule 40) — after a premature dead-end verdict wasted weeks of work

**What was built**:
- Layer 3: UnifiedEventEngine, TailRiskOverlay, MomentumSizer, SmartMoneySizing, VaultConsensusOverlay
- A1 asymmetric trade management (ATR-scaled stops, breakeven triggers, CEM gradual exits, time stops)
- Portfolio Exposure Governor (correlation monitoring, drawdown-reactive scaling, HL leverage enforcement)
- 15-agent deep audit found 53 bugs → rules 44-53 added
- Dead code archival: 36,658 LOC removed in a single PR (test count dropped from 4,542 to 3,610 — every removed test was testing dead code)
- Automated recalibration chain (daily short rescore, daily signal recalibration, weekly factor recalibration)

**What was learned**:
- 6 individually-accepted findings combined produced WORSE results than baseline — factorial interaction testing is mandatory
- Interface mismatches are the #1 silent killer — wrong attribute names caught by bare `except` made entire subsystems no-op
- `except Exception: pass` hid 4 critical bugs for weeks → now banned (Rule 45)
- State save/load asymmetry destroyed position data on restart → round-trip tests now mandatory (Rule 52)
- Dead code accumulates without active pruning — 19 dead modules discovered in single audit → per-PR audit now required (Rule 50)

**Metrics**: ~4,000 tests, ~900 backtests, 53 agent contract rules, 21 VRULEs

---

## S4 — Production Maturity (Current)

**Goal**: Deploy to mainnet with real capital. Achieve production-grade reliability, automated operations, and continuous self-improvement.

**Architecture**: 3-layer, 11-sleeve, live on Hyperliquid mainnet. AWS EC2 (Tokyo) with systemd orchestration.

**Key decisions**:
- Deployed to AWS Tokyo for low-latency proximity to Hyperliquid validators
- Systemd services for orchestrator + data collectors with automated restart
- Scheduled recalibration via systemd timers (daily short rescore, daily signal recal, weekly factor recal)
- Data plane verification rules (58-62) added after discovering state reconciliation bugs under live conditions
- Per-asset time stops and regime-aware trail modulation activated in production

**What was built**:
- Live execution bridge with signal suppression (prevents double-entry on restart)
- Multi-pool equity reader (standard perps + USDC + USDH + builder perp margin)
- Order validator with per-asset szDecimals and 5-sig-fig price precision enforcement
- Margin orchestrator for isolated margin pre-allocation on builder perps
- Collateral rebalancer for cross-pool margin management
- S4 target pipeline for calibrated per-asset performance targets
- Production deployment pipeline (SCP-based, not git — EC2 has no .git directory)

**What was learned**:
- Sleeve equity computed from config weights was 17x wrong — must sync from actual exchange margin allocations
- Builder perps (km:/xyz:) require completely separate routing paths from standard perps
- HL market orders need explicit limit price field — SDK does not auto-fill, orders silently rejected
- Signal suppression on restart prevents catastrophic double-entry (check existing positions before emitting orders)
- Live vs. paper mode selected once at startup via adapter injection — prevents mode-coupling bugs

**Metrics**: 4,376 tests across 323 files, 905+ PRs, 62 agent contract rules, 21 VRULEs, 900+ backtests

---

## The Arc

| Version | Tests | PRs | Rules | Status |
|---------|-------|-----|-------|--------|
| S1 | ~500 | ~50 | 10 | Paper trading, BTC-only |
| S2 | ~2,500 | ~400 | 43 | Paper trading, 11 sleeves |
| S3.x | ~4,000 | ~750 | 53 | Pre-production, research-hardened |
| **S4** | **4,376** | **905+** | **62** | **Live on mainnet** |

The progression is not just quantitative (more tests, more rules). Each version represents a qualitative shift:
- **S1 → S2**: From single-asset to multi-asset portfolio thinking
- **S2 → S3**: From feature accumulation to adversarial self-critique
- **S3 → S4**: From backtest artifact to production system managing real capital

The 62-rule agent contract, 21 VRULEs, and 81-hypothesis registry are not overhead — they are the primary intellectual output. The code is the implementation; the process artifacts are the knowledge.

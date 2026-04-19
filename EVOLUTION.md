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

**Metrics**: ~500 tests, ~50 backtests, 10 agent contract rules, 15 hypotheses

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
- Per-sleeve configuration system (100+ config files)
- SmartOrderRouter with 6 microstructure gates (VPIN, Kyle's Lambda, Vol regime, TFI, Cascade, RSI)
- Short basket engine with euphoria-fade scoring and weekly 6-factor rescore across 229-coin universe
- Data collection pipeline (25+ daemons: candles, L2, funding, OI, vault flows, sentiment)
- SQLite archive: 200M+ rows, ~40 GB, 3-tier isolation (cold/warm/hot)

**What was learned**:
- **Per-asset signal decomposition improved Sortino by +123%** — the single strongest meta-finding. Aggregate signals are almost always inferior to per-asset calibration.
- Naked shorts get liquidated in bull markets (VRULE-019) — 3-tier loss management is mandatory
- Dynamic leverage per regime is dead (VRULE-001) — static allocations with stress-based modulation outperform
- Strategy-mode engines lose to dual-EMA (VRULE-012) — complexity does not reliably beat simplicity
- Funding drag is per-asset, not uniform (VRULE-020) — original 0.01%/8h assumption was 16x wrong for BTC

**Metrics**: ~2,500 tests, ~500 backtests, 43 agent contract rules, 60+ hypotheses tracked

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
- 15-agent deep audit found 50+ bugs → entire audit-residue phase of rules added
- Dead code archival: tens of thousands of LOC removed in a single PR (test count dropped because every removed test was testing dead code — healthy shrink, not coverage loss)
- Automated recalibration chain (daily short rescore, daily signal recalibration, weekly factor recalibration)

**What was learned**:
- 6 individually-accepted findings combined produced WORSE results than baseline — factorial interaction testing is mandatory
- Interface mismatches are the #1 silent killer — wrong attribute names caught by bare `except` made entire subsystems no-op
- `except Exception: pass` hid 4 critical bugs for weeks → now banned (Rule 45)
- State save/load asymmetry destroyed position data on restart → round-trip tests now mandatory (Rule 52)
- Dead code accumulates without active pruning — 19 dead modules discovered in single audit → per-PR audit now required (Rule 50)

**Metrics**: ~4,000 tests, ~900 backtests, 50+ agent contract rules, 20+ VRULEs

---

## S4 — Production Maturity (Current)

**Goal**: Deploy to mainnet with real capital. Achieve production-grade reliability, automated operations, and continuous self-improvement.

**Architecture**: 3-layer, 11-sleeve, live on Hyperliquid mainnet. AWS EC2 (Tokyo) with systemd orchestration.

**Key decisions**:
- Deployed to AWS Tokyo for low-latency proximity to Hyperliquid validators
- Systemd services for orchestrator + data collectors with automated restart
- Scheduled recalibration via systemd timers (daily short rescore, daily signal recal, weekly factor recal, hourly builder perp candles)
- Data plane verification rules (58-62) added after discovering state reconciliation bugs under live conditions
- Per-asset time stops and regime-aware trail modulation activated in production
- Typed `VALENRunSpec` replaces string-argument launcher — encapsulates mode, config, data dir, execution intent, and calibration references in a single structured spec

**What was built**:
- Live execution bridge with signal suppression (prevents double-entry on restart)
- Multi-pool equity reader (standard perps + USDC + USDH + builder perp margin)
- Order validator with per-asset szDecimals and 5-sig-fig price precision enforcement
- Margin orchestrator for isolated margin pre-allocation on builder perps
- Collateral rebalancer for cross-pool margin management (USDH → USDC reverse swap)
- S4 utility-ranked target pipeline (`utility = adjusted_edge / downside_es`; greedy allocation within domain caps)
- Production deployment pipeline (SCP-based, not git — EC2 has no .git directory)
- Authority conflict map: 11 precedence pairs formally documented with per-pair risk assessment

**What was learned from live operation**:
- Sleeve equity computed from config weights was 17x wrong — must sync from actual exchange margin allocations
- Hyperliquid has three clearing houses (standard perps, builder perps, spot); `get_all_positions()` defaulted to only one, making builder perp positions invisible
- HL market orders need explicit limit price field — SDK does not auto-fill, orders silently rejected
- Signal suppression on restart prevents catastrophic double-entry (check existing positions before emitting orders)
- Live vs. paper mode selected once at startup via adapter injection — prevents mode-coupling bugs
- Reduce-only logic needs a restoration path when its input data normalizes — the vol-drift bug proved staleness semantics must be explicit

### S4 post-mainnet incidents (the part that only happens live)

Shipping to mainnet is a continuous event, not a deadline. Three weeks in:

**The 17x equity lie.** Internal `allocated_capital` of $4,616 for BTC while exchange margin was $272. Root: sleeve equity computed from config weights with no exchange reconciliation. Fix: Rules 58-62 (data plane verification) — all sizing reads from authoritative exchange state, reconciliation runs every N minutes, divergence above threshold blocks trading.

**Builder perps invisible.** `km:NVDA`, `km:RTX`, `km:PLTR`, `xyz:CL` are in a separate Hyperliquid clearing house. The default position-query API returned only standard perps. Real positions sat in a subsystem the orchestrator couldn't see. Rule 59: always query all clearing houses before reconciling.

**Vol-drift staleness (2026-04-17).** After a 5-day data outage and recovery, degenerate realized-vol readings (BTC 396%, AZTEC 486%) slashed 6 sleeves to 0.5-1.6x leverage floors. The reduce-only vol-drift logic had no restoration path; overrides persisted in state forever. Capital deployment stuck at 17.8%. Fix: drop overrides on restart under three specific conditions (flat-at-shutdown, equity-rescaled, hedge-sleeve-exempt). Deployment recovered to 95%. Full story in [PROBLEMS_SOLVED.md](PROBLEMS_SOLVED.md#1-the-stale-vol-drift-bug).

**Dual ModeManager.** Authority conflict audit found two independent `ModeManager` instances (orchestrator + S4) that could silently disagree. No test caught this because each instance was locally correct. Remediation in progress: single source of truth with the S4 instance reading from the orchestrator.

**L3 silently dead.** 5 of 6 L3 sizing components producing nothing for 4 weeks after S4 cutover. Each unit test passed; the pipeline-level behavior was a bypass. Institutional response: pipeline-scope sizing traces; components must report what they *caused*, not what they *computed*.

**Metrics**: **5,000+ tests · 1,000+ PRs · 60+ agent contract rules · 20+ VRULEs · 120+ hypotheses · 900+ backtests**

---

## The Arc

| Version | Tests | PRs | Rules | Hypotheses | Status |
|---------|-------|-----|-------|------------|--------|
| S1 | ~500 | ~50 | ~10 | ~15 | Paper trading, BTC-only |
| S2 | ~2,500 | ~400 | ~40 | ~60 | Paper trading, 11 sleeves |
| S3.x | ~4,000 | ~750 | ~50 | ~100 | Pre-production, research-hardened |
| **S4** | **5,000+** | **1,000+** | **60+** | **120+** | **Live on mainnet** |

Exact counts drift daily; the table uses conservative round-number floors. What scales is not test count — what scales is the *ratio of encoded institutional knowledge* (agent rules + VRULEs + hypothesis registry) to raw lines of code.

The progression is not just quantitative (more tests, more rules). Each version represents a qualitative shift:

- **S1 → S2**: From single-asset to multi-asset portfolio thinking. The per-asset decomposition finding (+123% Sortino) emerged here and became the strongest meta-principle.
- **S2 → S3**: From feature accumulation to adversarial self-critique. The 15-agent deep audit, the factorial interaction failure (6 good findings combined worse than baseline), the VRULE overturn (VRULE-017 CEM) all happened in this phase.
- **S3 → S4**: From backtest artifact to production system managing real capital. Paper mode hides an entire class of bugs — state divergence, clearing-house invisibility, stale-override persistence, observational silence. S4's hardening is mostly debugging the failure modes that only exist under real trading conditions.

The agent contract, VRULE registry, and hypothesis registry are not overhead — **they are the primary intellectual output.** The code is the implementation; the process artifacts are the knowledge. If I had to rebuild VALEN from scratch tomorrow, the rules, VRULEs, and hypothesis registry would get me there 10x faster than the code itself.

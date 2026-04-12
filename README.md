
```
██╗   ██╗ █████╗ ██╗     ███████╗███╗   ██╗
██║   ██║██╔══██╗██║     ██╔════╝████╗  ██║
██║   ██║███████║██║     █████╗  ██╔██╗ ██║
╚██╗ ██╔╝██╔══██║██║     ██╔══╝  ██║╚██╗██║
 ╚████╔╝ ██║  ██║███████╗███████╗██║ ╚████║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝
```

# VALEN — Multi-Asset Algorithmic Trading System

**Live on Hyperliquid mainnet since April 4, 2026.** 3-layer architecture, 11 independent sleeves, 4,376 tests. Designed and built in ~4 weeks by a solo product/engineering leader operating a fleet of AI agents, leveraging architecture patterns refined across 7 prior system versions.

> This is a portfolio showcase. The full codebase (905+ PRs, ~150K LOC) lives in a private repository.

---

## About the Builder

I'm a product and engineering leader with 10+ years of experience building and exiting startups. My career has been 0-to-1 and 1-to-10: defining products, hiring teams, shipping systems, and finding market fit.

VALEN represents a new model: **the full-stack founder who architects complex systems and operates AI agent fleets as force multipliers.** I didn't write 150K lines of Python by hand. I designed the architecture, defined the 62-rule agent contract that encodes my engineering judgment, directed research campaigns across 81 hypotheses, and operated the AI agents that implemented it. The system reflects my decisions — what to build, what to kill, how components interact, and when to ship.

The relevant skill is not "can write Python." It's: can I take a complex domain (quantitative trading on a novel DEX), architect a production system, operate AI at scale to build it, and ship it live with real capital in weeks instead of quarters?

---

## System at a Glance

| | |
|---|---|
| **Status** | Live on Hyperliquid mainnet, AWS Tokyo |
| **Version** | S4 — designed and built in ~4 weeks (March-April 2026) |
| **Architecture** | 3-layer (Signal → Execution → Sizing), 11 sleeves, Clean Architecture |
| **Scale** | 4,376 tests, 905+ PRs, ~150K LOC, 109 config files |
| **Research** | 81 hypotheses tested, 21 dead-ends documented, 900+ backtests |
| **Data** | 28 daemons, 208M+ rows, 18 databases, 3-tier isolation |
| **Operations** | Automated daily/weekly recalibration, 5-min health checks |
| **AI process** | 62-rule agent contract, git worktree isolation, conflict preflight |

**[Live performance data →](PERFORMANCE.md)** | **[System evolution S1-S4 →](EVOLUTION.md)**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: SIGNAL                                                │
│  Per-sleeve dual-EMA crossover + regime gate                    │
│  Direction decisions at 4h+ cadence only                        │
│  Invariant: Sub-hourly direction changes BANNED (0% pass rate)  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: EXECUTION                                              │
│  SmartOrderRouter: 6 microstructure gates (VPIN, Kyle's Lambda, │
│  vol regime, TFI, cascade suppression, RSI)                     │
│  Routes: ALO maker 1.5bps vs MARKET taker 4.5bps               │
│  Invariant: L2 NEVER overrides L1 direction                     │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: EVENT / SIZING                                        │
│  5 overlays + A1 trade management (ATR stops, breakeven, CEM)   │
│  Hierarchical stacking: MAX(boosts), MIN(reductions)            │
│  Invariant: L3 scales size but NEVER flips direction            │
└─────────────────────────────────────────────────────────────────┘
```

### Portfolio

| | Sleeves | Composition |
|---|---|---|
| **Long Book** | 10 | BTC, HYPE, SKY, Oil (xyz:CL), AZTEC, PAXG, RENDER, NVDA (km:), RTX (km:), PLTR (km:) |
| **Hedge Book** | 1 | 30-coin inverse-vol-weighted short basket, euphoria-fade scoring, 3-tier loss management |

`km:` = builder perps (institutionally licensed TradFi instruments on Hyperliquid). `xyz:` = commodity perps.

### Clean Architecture

Domain models (Pydantic v2, `Decimal` for money) → Ports (4 abstract interfaces) → Services → Adapters (Hyperliquid SDK, paper trading, backtest engine). Import boundaries enforced by CI. Backtest and live adapters implement identical port contracts.

---

## What Was Tested and Killed

The system is defined as much by its 21 documented rejections as by what survived:

| Verdict | Finding |
|---------|---------|
| VRULE-001 | Dynamic leverage per regime: dead |
| VRULE-012 | Strategy-mode engines lose to dual-EMA |
| VRULE-013 | Cross-exchange derivatives: zero alpha (331K hourly obs) |
| VRULE-019 | Naked shorts liquidated in bull markets |
| VRULE-020 | Funding drag per-asset, not uniform (original model 16x wrong) |
| VRULE-021 | Mean reversion during sideways loses to holding |

**Strongest meta-finding:** Per-asset signal decomposition improved Portfolio Sortino by +123% vs aggregate signals. Every threshold, stop width, and modulation frequency is now asset-specific.

All 81 hypotheses follow: Hypothesis → Test Plan → Kill Criteria → Factorial Campaign → Temporal Red-Team → Verdict. Details in [METHODOLOGY.md](METHODOLOGY.md).

---

## Code Samples

These are production files from the private repository. Signal parameters and scoring formulas are not included.

| File | What It Demonstrates |
|------|---------------------|
| [`src/services/execution/vpin_calculator.py`](src/services/execution/vpin_calculator.py) | VPIN toxicity estimation (Easley et al. 2012) — volume bucketing, BVC classification, streaming + batch interfaces, per-asset calibration |
| [`src/domain/models.py`](src/domain/models.py) | Pydantic v2 domain models — `Decimal` financials, frozen immutability, exchange-agnostic design |
| [`src/ports/`](src/ports/) | 4 port interfaces — the complete boundary between domain logic and infrastructure |
| [`src/backtesting/fee_model.py`](src/backtesting/fee_model.py) | Canonical fee model — single source of truth, self-validating, zero-fee leverage awareness |
| [`tests/test_integration_contracts.py`](tests/test_integration_contracts.py) | Interface contract tests — the fix for the #1 bug category (silent attribute name mismatches) |
| [`scripts/conflict_preflight.sh`](scripts/conflict_preflight.sh) | Multi-agent coordination — PR conflict detection, exclusive zone enforcement, worktree management |

---

## AI Fleet Operation

I built the harness, not just the system. VALEN's development infrastructure is a product in itself:

- **62-rule agent contract** — started at 10, grew through production incidents. Each rule traces to a specific bug. This is encoded institutional knowledge, not a style guide.
- **Git worktree isolation** — each agent works in its own worktree. No file conflicts, clean merge paths, failure isolation.
- **Conflict preflight** — agents check for exclusive zone contention before starting work. Exit code 2 = stop.
- **Merge orchestrator** — computes safe PR merge order based on file dependency analysis.
- **Verification gate** — lint + type check + 4,376 tests + architecture conformance before every merge.

The 62 rules evolved in phases: foundation (1-10), research discipline (11-28), research failure prevention (29-38), deep audit findings (44-53), and live deployment (54-62). Each phase was triggered by a class of failure that the previous rules didn't prevent.

A 15-agent parallel audit found 53 bugs in a single session — interface mismatches, silent exceptions, state persistence failures, dead code. That session produced rules 44-53 and 12 fix PRs.

See [AI_DEVELOPMENT.md](AI_DEVELOPMENT.md) for the full breakdown.

---

## Production Operations

```
AWS EC2 Tokyo → systemd services (orchestrator + vault flow collector)
             → systemd timers (daily short rescore, daily signal recal, weekly factor recal)
             → 28 data collection daemons (candles, L2, funding, OI, sentiment, vaults)
             → 208M+ rows across 18 SQLite databases (cold/warm/hot tier isolation)
```

Health checks every 5 minutes. Economics gate blocks trades where edge-to-cost ratio < 1.3x. Currently running at 0.69x gross leverage — the system prefers sitting flat to paying fees on marginal signals. [Live data →](PERFORMANCE.md)

---

## Lessons for Engineering Teams

1. **Interface contract tests prevent the #1 integration bug.** Verify attribute names match between producer and consumer. `pct_change` vs `change_pct` made an entire subsystem a no-op.
2. **`except Exception: pass` is a time bomb.** Four critical bugs were hidden for weeks by bare exception handlers. Ban them.
3. **Independently-validated improvements don't compose.** Six accepted findings combined produced WORSE results than baseline. Pairwise interaction testing is mandatory.
4. **Canonical models beat per-script constants.** Three different fee rates in three scripts, all wrong. Single source of truth, imported everywhere.
5. **Active deletion is a feature.** 36,658 LOC of dead code archived in a single PR. Without active pruning, dead code grows faster than live code.

## Lessons for AI-Enabled Product Teams

1. **The harness is the product.** The 62-rule agent contract, conflict preflight, and merge orchestrator are more valuable than any individual PR. They encode judgment that applies to every future session.
2. **Rules should grow from incidents, not imagination.** Every rule traces to a specific failure. Speculative rules get ignored; incident-driven rules get respected.
3. **Session typing prevents mode-mixing.** Research sessions (exploratory, throwaway code OK) vs implementation sessions (full verification, contract tests) vs audit sessions (adversarial, trying to break things). Different quality bars for different work.
4. **AI agents need boundaries, not babysitting.** Worktree isolation, conflict preflight, and verification gates let agents work autonomously. The constraint system replaces micromanagement.
5. **Encode what you learned, not what you did.** The hypothesis registry and VRULE system prevent re-investigating dead ends. The cost of a well-documented rejection is negative — it saves future time.

---

## Timeline (Honest)

| Date | Milestone |
|------|-----------|
| Pre-March 2026 | EISEN S1-S7 on Coinbase (predecessor system, 7 architecture versions) |
| Early March | VALEN S1: Clean Architecture foundation, BTC-only, ports & adapters |
| Mid March | S2: 11-sleeve expansion, short basket, SmartOrderRouter, 28 data daemons |
| Late March | S3: Research hardening, 81 hypotheses, 21 VRULEs, 15-agent deep audit |
| April 4 | **S4: Live on Hyperliquid mainnet** with real capital |
| April 6-10 | EC2 Tokyo migration, 5-day system rebuild, 30+ live bug fixes |
| April 11+ | Stable production operation, automated recalibration |

S1 through S4 happened in approximately 4 weeks. This speed was possible because (a) EISEN provided 7 versions of architectural refinement to draw from, (b) AI agents handled implementation at ~20-30 PRs/day during peak sessions, and (c) the hypothesis-driven methodology killed bad ideas fast instead of letting them accumulate.

---

## Related

- **[EISEN](https://github.com/raydeoliveira/eisen-portfolio)** — predecessor system for Coinbase. 7 versions, 4 strategy eliminations.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — full architecture deep-dive
- **[PERFORMANCE.md](PERFORMANCE.md)** — live trading data with charts
- **[EVOLUTION.md](EVOLUTION.md)** — S1 → S4 version narrative
- **[METHODOLOGY.md](METHODOLOGY.md)** — research framework (factorial campaigns, temporal red-teaming)
- **[ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)** — coding standards, each with the bug that motivated it
- **[AI_DEVELOPMENT.md](AI_DEVELOPMENT.md)** — multi-agent coordination infrastructure

---

*Built by [Ray De Oliveira](https://github.com/raydeoliveira) — product leader, systems architect, AI fleet operator.*

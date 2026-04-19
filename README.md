
```
██╗   ██╗ █████╗ ██╗     ███████╗███╗   ██╗
██║   ██║██╔══██╗██║     ██╔════╝████╗  ██║
██║   ██║███████║██║     █████╗  ██╔██╗ ██║
╚██╗ ██╔╝██╔══██║██║     ██╔══╝  ██║╚██╗██║
 ╚████╔╝ ██║  ██║███████╗███████╗██║ ╚████║
  ╚═══╝  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝
```

# VALEN — Multi-Asset Algorithmic Trading System

**Live on Hyperliquid mainnet since April 4, 2026.** 3-layer architecture, 11 independent sleeves, 5,000+ tests. Designed and shipped in ~4 weeks by a solo product/engineering leader operating a fleet of AI agents, building on patterns refined across 7 prior system versions.

> This is a portfolio showcase. The full codebase (1,000+ PRs, ~150K LOC) lives in a private repository.

---

## What this repo demonstrates

Most portfolio projects show finished code. This one shows **how a solo operator builds a production system with real capital on the line** — the architectural decisions, the bugs that surfaced at 3 AM on mainnet, the rules that had to exist before the next session didn't reintroduce the last one's failure.

If you're evaluating technical judgment, I'd point to:

- **[PROBLEMS_SOLVED.md](PROBLEMS_SOLVED.md)** — eight flagship engineering war stories. Each one has a wrong first hypothesis, a forensic process, a root cause, and institutional residue. The staleness bug that froze 80%+ of capital behind ghost state. The 15-agent audit that found 50+ bugs in a single day. The "edge is in the exit, not the entry" finding that inverted an entire research program. **Read this first if you want signal on how I reason.**
- **[AI_DEVELOPMENT.md](AI_DEVELOPMENT.md)** — the agentic harness. The 60+-rule agent contract wasn't designed in advance; it grew from production incidents. Git worktree isolation, conflict preflight, merge orchestration, and session-typed development let 15 agents work in parallel without stepping on each other.
- **[METHODOLOGY.md](METHODOLOGY.md)** — 120+ hypotheses tested, 21 dead-end verdicts documented (VRULEs), 900+ backtests logged. Hypothesis-driven development with pre-declared kill criteria, factorial interaction tests, and adversarial VRULE review.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Clean Architecture with CI-enforced import boundaries, 4 port interfaces, and identical backtest/live adapter contracts. Infrastructure details are implementation details; the domain is exchange-agnostic.

---

## About the builder

I'm a product and engineering leader with 10+ years of experience building and exiting startups. My career has been 0-to-1 and 1-to-10: defining products, hiring teams, shipping systems, finding market fit.

VALEN represents a new operating model: **the full-stack founder who architects complex systems and operates AI agent fleets as force multipliers.** I didn't write 150K lines of Python by hand. I designed the architecture, wrote the 60+-rule agent contract that encodes my engineering judgment, directed research campaigns across 120+ hypotheses, and operated the fleet that implemented it. The system reflects my decisions — what to build, what to kill, how components interact, when to ship.

The relevant skill isn't "can write Python." It's: can I take a complex, novel domain (quantitative trading on a frontier DEX), architect a production system, operate AI at scale to build it, and ship it live with real capital in weeks instead of quarters — and then debug it under production stakes when it inevitably surprises me?

---

## System at a glance

| | |
|---|---|
| **Status** | Live on Hyperliquid mainnet, AWS EC2 Tokyo (ap-northeast-1) |
| **Version** | S4 — designed, shipped, and hardened March-April 2026 |
| **Architecture** | 3-layer (Signal → Execution → Sizing), 11 sleeves, Clean Architecture |
| **Scale** | **5,000+ tests · 1,000+ PRs · ~150K LOC · 100+ config files** |
| **Research** | **120+ hypotheses tested · 20+ documented dead-ends · 900+ backtests** |
| **Data** | 25+ collection daemons · 200M+ archive rows · 18 SQLite databases · 3-tier access isolation |
| **Operations** | Automated daily/weekly recalibration, 5-min health checks, systemd timers |
| **AI process** | **60+-rule agent contract · git worktree isolation · conflict preflight · merge orchestrator** |

**[Live performance →](PERFORMANCE.md)** · **[Evolution S1→S4 →](EVOLUTION.md)** · **[War stories →](PROBLEMS_SOLVED.md)**

---

## Architecture (summarized)

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: SIGNAL                                                 │
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
│  S4 utility-ranked target pipeline · A1 asymmetric trade mgmt   │
│  Authority map: 11 documented precedence pairs                  │
│  Invariant: L3 scales size but NEVER flips direction            │
└─────────────────────────────────────────────────────────────────┘
```

**Portfolio:** 10-sleeve long book (BTC, HYPE, SKY, Oil via `xyz:CL`, AZTEC, PAXG, RENDER, NVDA/RTX/PLTR via `km:` builder perps) plus a 1-sleeve hedge book that runs a dynamic short basket with euphoria-fade scoring, weekly 6-factor rescore across the 229-coin HL universe, and 3-tier loss management.

Full architecture in [ARCHITECTURE.md](ARCHITECTURE.md). The interesting parts aren't the layer boundaries — those are standard Clean Architecture. The interesting parts are the **invariants that enforce them:** CI-enforced import rules, contract tests for every cross-component boundary, and a documented authority map for every case where two policies might disagree about the same decision.

---

## Signal from the numbers

The scale is not the point. The discipline behind the scale is the point.

AI-augmented development makes it cheap to inflate headline numbers, so these only matter in context:

- **5,000+ tests** isn't impressive as a count; it's impressive as a ratio to the bugs it has caught. A 15-agent deep audit found 50+ bugs in a single session. Every one generated a test that makes recurrence impossible. Test count grows from failure, not from completion metrics.
- **1,000+ PRs** looks like velocity. It's actually filter. The PR template requires a quantitative verification number for every performance claim, an explicit long-vs-short symmetry declaration, a dead-code audit, and a factorial interaction test if the change touches an accepted finding. Most rejected PRs fail the verification number requirement.
- **120+ hypotheses tested** isn't a measure of experimentation — it's a measure of *killed ideas*. Roughly half of all hypotheses end in a KILL, REJECT, or FAIL verdict. The ones that reach VRULE status prevent future research from re-investigating them.
- **60+-rule agent contract** isn't a style guide. Every rule traces to a specific incident. Rule 45 exists because four bugs hid behind `except Exception: pass` for weeks. Rule 37 exists because three scripts had three different fee rates, all wrong. The rules *grew from incidents, not from imagination.*

---

## What was tested and killed

The system is defined as much by its documented rejections as by what survived:

| Verdict | Finding |
|---------|---------|
| VRULE-001 | Dynamic leverage per regime is dead |
| VRULE-012 | Strategy-mode engines lose to dual-EMA |
| VRULE-013 | Cross-exchange derivatives: zero alpha (331K hourly obs) |
| VRULE-014 | SPX (km:US500) data before 2026-03-18 is CORRUPTED |
| VRULE-019 | Naked shorts liquidated in bull markets — 3-tier loss mgmt required |
| VRULE-020 | Funding drag is per-asset (original model 16x wrong for BTC) |
| VRULE-021 | Mean reversion during sideways loses to holding |

**Strongest meta-finding:** per-asset signal decomposition improved Portfolio Sortino by +123% vs aggregate signals. Every threshold, stop width, and modulation frequency in the system is now asset-specific. This became Rule 39: every new mechanism must justify why an aggregate parameter is defensible vs. a per-asset one.

**The VRULE Overturn:** VRULE-017 was declared based on a test with dead signals, BTC-only data, and wrong fee accounting. When overturned, weeks of work had been skipped. Rule 40 now requires every VRULE to survive adversarial review on four dimensions: right data, right assets (multi-asset not BTC-only), right fee model, right signals. Premature VRULEs waste more time than premature acceptance.

Full methodology, kill criteria, factorial campaign design, and temporal red-team procedures in [METHODOLOGY.md](METHODOLOGY.md).

---

## Code samples

Production files from the private repository. Signal parameters and scoring formulas are withheld.

| File | What it demonstrates |
|------|---------------------|
| [`src/services/execution/vpin_calculator.py`](src/services/execution/vpin_calculator.py) | VPIN toxicity estimation (Easley et al. 2012) — volume bucketing, BVC classification, streaming + batch interfaces, per-asset calibration |
| [`src/domain/models.py`](src/domain/models.py) | Pydantic v2 domain models — `Decimal` financials, frozen immutability, exchange-agnostic design |
| [`src/ports/`](src/ports/) | 4 port interfaces — the complete boundary between domain logic and infrastructure |
| [`src/backtesting/fee_model.py`](src/backtesting/fee_model.py) | Canonical fee model — single source of truth, self-validating, zero-fee leverage awareness |
| [`tests/test_integration_contracts.py`](tests/test_integration_contracts.py) | Interface contract tests — the fix for the #1 bug category (silent attribute name mismatches) |
| [`scripts/conflict_preflight.sh`](scripts/conflict_preflight.sh) | Multi-agent coordination — PR conflict detection, exclusive zone enforcement, worktree management |

---

## AI fleet operation

**I built the harness, not just the system.** VALEN's development infrastructure is the part that generalizes.

- **60+-rule agent contract** — started at 10, grew through production incidents. Each rule traces to a specific bug and includes a *why* annotation so the agent can reason about edge cases rather than blindly follow.
- **Git worktree isolation** — each agent works in its own worktree. No file conflicts, clean merge paths, failure isolation.
- **Conflict preflight** — agents check for exclusive zone contention before starting work. Exit code 2 = stop. Prevents the cascading merge conflict problem that plagues naive parallel development.
- **Merge orchestrator** — computes safe PR merge order based on file dependency analysis. Replaced the "merge and hope" pattern that created integration failures.
- **Verification gate** — lint + type check + full test suite + architecture conformance, all before merge. Import-boundary rules are CI-enforced, not convention.
- **Session typing** — research sessions, implementation sessions, audit sessions, and production sessions have different tolerances, verification bars, and merge protocols. Mode-mixing was a failure class; session typing prevents it.

The rules evolved in phases: foundation → research discipline → research failure prevention → meta-findings encoded as rules → deep audit residue → live deployment and data plane. **Each phase was triggered by a class of failure that the previous phase didn't prevent.**

A 15-agent parallel audit found dozens of bugs in a single session — interface mismatches, silent exceptions, state persistence failures, dead code. That session produced an entire phase of the agent contract and a batch of merged fix PRs in a single day.

Full breakdown, including per-rule incident traces, in [AI_DEVELOPMENT.md](AI_DEVELOPMENT.md).

---

## Production operations

```
AWS EC2 Tokyo (ap-northeast-1)
    │
    ├── valen.service               (main orchestrator, systemd)
    ├── valen-smart-money.service   (smart-money positioning collector)
    │
    ├── systemd timers:
    │     ├── valen-candle-collector     (4h + 1h + 15m OHLCV for 11 sleeves)
    │     ├── valen-short-rescore        (daily short-basket recompute)
    │     ├── valen-recalibration        (daily signal recal)
    │     ├── valen-factor-recal         (weekly factor recal)
    │     ├── valen-builder-perp-candles (hourly km:/xyz: candles)
    │     └── valen-coinalyze-collector  (cross-exchange OI/funding)
    │
    └── 25+ data collection daemons
          → 200M+ rows across 18 SQLite databases
          → 3-tier access isolation (cold archive / warm daemon DBs / hot live API)
```

Health checks every 5 minutes. Economics gate blocks trades where edge-to-cost ratio < 1.3x. Signal suppression on restart prevents double-entry after downtime. State reconciliation against exchange state is mandatory before any sizing decision (data plane verification rules).

[Live performance data →](PERFORMANCE.md)

---

## Lessons for engineering teams

1. **Interface contract tests prevent the #1 integration bug.** Verify attribute names match between producer and consumer. `pct_change` vs `change_pct` turned an entire subsystem into a no-op for 3 weeks.
2. **`except Exception: pass` is a time bomb.** Four critical bugs hid behind bare exception handlers. Ban them, grep-enforce the ban in CI.
3. **Independently-validated improvements don't compose.** Six accepted findings combined produced worse results than baseline. Pairwise interaction testing is mandatory before simultaneous deployment.
4. **Canonical models beat per-script constants.** Three different fee rates in three scripts, all wrong. Single source of truth, imported everywhere, grep-enforced.
5. **Active deletion is a feature.** Tens of thousands of lines of dead code archived in a single PR. Without active pruning, dead code grows faster than live code.
6. **Internal state and exchange state are independent facts.** The system's belief about its positions must be mechanically reconciled against the exchange's ground truth. Paper-mode testing cannot surface this class of bug.

## Lessons for AI-enabled product teams

1. **The harness is the product.** The agent contract, conflict preflight, and merge orchestrator are more valuable than any individual PR. They encode judgment that applies to every future session.
2. **Rules should grow from incidents, not imagination.** Every rule traces to a specific failure. Speculative rules get ignored; incident-driven rules get respected. Each rule has a *why* so the agent can reason at edge cases.
3. **Session typing prevents mode-mixing.** Research sessions (exploratory) vs implementation sessions (strict verification) vs audit sessions (adversarial) vs production sessions (safety-critical) have different quality bars. Don't mix them.
4. **AI agents need boundaries, not babysitting.** Worktree isolation, conflict preflight, and verification gates let agents work autonomously. The constraint system replaces micromanagement.
5. **Encode what you learned, not what you did.** The hypothesis registry and VRULE system prevent re-investigating dead ends. The cost of a well-documented rejection is *negative* — it saves future time.
6. **Adversarial scoping beats exhaustive scanning.** 15 agents with specific threat models in parallel triangulate on categorical findings. The intersection across multiple agents is the highest-signal signal.

---

## Timeline (honest)

| Date | Milestone |
|------|-----------|
| Pre-March 2026 | EISEN S1-S7 on Coinbase (predecessor system, 7 architecture versions) |
| Early March | **VALEN S1**: Clean Architecture foundation, BTC-only, ports & adapters |
| Mid March | **S2**: 11-sleeve expansion, short basket, SmartOrderRouter, 25+ data daemons |
| Late March | **S3**: Research hardening, 120+ hypotheses, 20+ VRULEs, 15-agent deep audit |
| **April 4** | **S4: Live on Hyperliquid mainnet** with real capital |
| April 6-10 | EC2 Tokyo migration, 5-day infrastructure hardening, 30+ live bug fixes |
| April 11-13 | First post-mainnet incidents: data-plane drift, builder perp invisibility |
| April 17 | **Vol-drift staleness bug diagnosed and fixed** — capital deployment recovered from 17.8% to 95% |
| April 18-19 | Authority conflict audit, state save/load symmetry audit, IC analysis |

S1 through S4 happened in approximately 4 weeks. The post-April work reflects what happens after you go live: the bugs that only appear under real trading conditions, the state divergences that paper mode can't reveal, the policies that were locally correct and globally incoherent. The speed was possible because (a) EISEN provided 7 versions of architectural refinement to draw from, (b) AI agents handled implementation at ~20-30 PRs/day during peak sessions, and (c) hypothesis-driven methodology killed bad ideas fast instead of letting them accumulate.

---

## Related reading

- **[PROBLEMS_SOLVED.md](PROBLEMS_SOLVED.md)** — 8 flagship engineering war stories with forensic detail. *Start here for engineering signal.*
- **[AI_DEVELOPMENT.md](AI_DEVELOPMENT.md)** — multi-agent coordination, agent contract evolution, 15-agent deep audit
- **[METHODOLOGY.md](METHODOLOGY.md)** — hypothesis-driven research, factorial campaigns, temporal red-teaming, VRULE review
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — 3-layer architecture, port interfaces, hierarchical sizing, authority map
- **[EVOLUTION.md](EVOLUTION.md)** — S1 → S4 version narrative with scale metrics at each stage
- **[ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md)** — coding standards, each with the bug that motivated it
- **[PERFORMANCE.md](PERFORMANCE.md)** — live trading data with normalized charts
- **[EISEN](https://github.com/raydeoliveira/eisen-portfolio)** — predecessor system for Coinbase. 7 versions, 4 strategy eliminations.

---

*Built by [Ray De Oliveira](https://github.com/raydeoliveira) — product leader, systems architect, AI fleet operator.*

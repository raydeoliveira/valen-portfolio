# Flagship Problems Solved

A production trading system with real capital does not reveal its interesting problems in design documents. They surface at 3 AM when the equity curve flatlines and the dashboard disagrees with the exchange. This document captures eight of those moments — the sophisticated ones, the ones where the first hypothesis was wrong, where the easy fix would have created worse bugs, and where the right answer required pulling on a thread until the entire failure mode was visible.

Each story follows the same structure: **Observed symptom → First (wrong) hypothesis → Forensic process → Root cause → Fix → Institutional residue.** The last field matters most. Every war story here ended with a new engineering rule, a new test class, a new invariant, or a new piece of automation that makes the class of bug impossible to recur. That residue is the actual product.

---

## 1. The Stale Vol-Drift Bug: 82% of Capital Frozen by Ghost State

**Date:** 2026-04-17 · **Stakes:** Live capital, mainnet · **Time to diagnosis:** ~4 hours

### Observed symptom

Live orchestrator heartbeat after an EC2 restart: account equity $10,062, but only $1,791 deployed. **Capital utilization: 17.8%.** Seven of ten long sleeves sitting flat despite no obvious signal failures. From a fleet operator's perspective, this is the worst kind of bug — nothing is broken *loudly*, the system is just quietly failing to do its job.

### First hypothesis (wrong)

*"The system has converged to a 3-sleeve reality at current equity scale. The $250 min-notional filter is correctly suppressing sub-scale sleeves. This is by design."*

This explanation was plausible: the min-notional gate exists precisely to prevent entries that can't cover round-trip fees. At $10K equity with conservative per-sleeve weights, several sleeves would indeed fall below $250 notional. A casual investigation could have stopped here and added a "works as designed" comment to the ticket.

### What broke the first hypothesis

Walking the math per-sleeve revealed inconsistencies the first hypothesis could not explain. BTC's computed target was $169 — below the $250 floor. But why was BTC's *leverage* at 0.5x? The config file specified 3x. Something had capped it.

Reading `_check_vol_leverage_drift()` line by line: the function *only reduces* leverage when realized vol exceeds implied. There is no restoration path. Reduce-only.

Searching the state file for `vol_drift_overrides`:

```json
{
  "btc":   {"leverage": 0.5, "reason": "realized_vol=396.4%"},
  "aztec": {"leverage": 0.6, "reason": "realized_vol=486.0%"},
  ...
}
```

BTC realized vol of **396%** is not a market condition. Real BTC vol is 50-80%. AZTEC at 486% is similarly absurd. These numbers were *artifacts*, not measurements.

### Root cause (two layers deep)

Five days earlier, the system had suffered a data pipeline outage. When it came back up, `_check_vol_leverage_drift()` computed realized vol from the recovery candles — which, because the exchange had synthesized flat candles during the downtime, were all identical-return bars. Variance of identical returns is computed over a windowed product that, in the degenerate case, produces arbitrarily large numbers. The vol function saw "396%" and correctly slashed BTC leverage to floor — a perfectly reasonable response to an impossible-looking market.

Then the degenerate readings disappeared when real candles returned. But the *overrides* persisted in state. Reduce-only has no restore path. Six sleeves stayed frozen at 0.5-1.6x leverage floors forever, set by a ghost of a 5-day-old data outage.

### The wrong fix (and why it was tempting)

Lowering `min_target_notional_usd_default` from $250 to $100 would have "fixed" the symptom — more sleeves would clear the gate. But the gate exists because round-trip fees of $0.135 exceed typical daily carry at $100 notional. The wrong fix would have silently broken the fee economics that keeps the system solvent on marginal edges.

The discipline here: **separate legitimate filters from bug-induced filters.** The min-notional floor was legitimate. The vol-drift overrides were bugs. Conflating them would have preserved both problems.

### The right fix

Drop stale `vol_drift_overrides` on restart under three specific conditions:

1. **Sleeve was FLAT at shutdown.** No open position means no ongoing positive data can maintain the override. A vol override on a closed sleeve is, by definition, obsolete.
2. **Hedge sleeve.** The short basket is already exempt from vol-drift reduction by design — so a persistent override on it is a definitional bug.
3. **Equity rescaled >2x or <0.5x.** The override was calibrated for a different capital base; it shouldn't carry across a meaningful rescale event.

Open positions with real vol data are unaffected. The protective behavior that prevented a 25% NVDA drawdown from cascading two weeks earlier — unchanged.

### Result

`vol_drift_overrides: {}` after restart. Capital deployment climbed from 17.8% to 95%. Five active targets with clean economics.

### Institutional residue

- New save/load symmetry audit rule: every stateful field must declare its staleness semantics ("stale on restart" / "stale on equity rescale" / "never stale").
- Rule 60 (data plane verification): always verify internal state against exchange-observable state at restart.
- A new class of test: **asymmetric-recovery tests** — simulate the exact scenario where reduce-only logic meets transient bad data, and verify the system recovers when data normalizes.

**Why this story matters to engineering leaders:** A junior engineer would have lowered min_notional. A senior engineer would have found the vol overrides. A staff engineer would have asked *why* reduce-only logic existed and preserved that protection while fixing the staleness. The final fix is a four-line diff. The reasoning behind those four lines is what makes it right.

---

## 2. The 15-Agent Deep Audit: 53 Bugs in One Session

**Date:** S3.x research-hardening phase · **Stakes:** Pre-production confidence · **Outcome:** 12 merged PRs, 10 new engineering rules

A single-agent code review finds surface bugs. I wanted the adversarial kind — the ones that only surface when 15 different lenses are applied in parallel, each specialized to hunt a specific class of failure.

### Design

Each agent got a targeted audit scope, an explicit threat model, and hours to run unsupervised. They operated in isolated git worktrees with no coordination except through merged PRs.

| Agent | Threat model | Bugs |
|-------|--------------|------|
| Signal integrity | L1 sleeves firing correctly? | 5 — dead sleeves, EMA config drift |
| Execution layer | SOR state + routing decisions | 4 — thread-unsafe counters, gate arithmetic |
| State persistence | Round-trip save/load symmetry | 3 — positions wiped, equity reset, PnL lost |
| Interface contracts | Producer/consumer attribute match | 6 — `pct_change` vs `change_pct` class |
| Exception handling | Silent `except` masking bugs | 8 — AttributeError/ImportError swallowed |
| Dead code | Unused modules/methods | 19 modules identified |
| Data access | SQLite concurrency patterns | 4 — missing busy_timeout, unbounded queries |
| Configuration | Default factory purity | 3 — network I/O in dataclass defaults |
| *Others* | Mixed | 1 |

**53 bugs. One session. 12 PRs merged in a single day.**

### The most important finding wasn't a bug — it was a category

Six separate agents independently flagged the same pattern: `except Exception: pass`. Four instances were actively hiding real failures. The recalibrator had been dead for an entire development session — every run threw `AttributeError` caught by a bare except, logged nothing, and the orchestrator consumed the cached (stale) result with no indication anything had gone wrong.

This was not a bug. This was a **bug class**. Rule 45 emerged: silent exception swallowing is banned. Every `except` must log or re-raise. The architecture-conformance check in CI now greps for the pattern and fails PRs that reintroduce it.

### Why adversarial scoping works

Each agent had one job and went deep. No agent worried about "is this the most important thing?" — the threat model was pre-assigned. The intersection across all 15 agents — the ideas that surfaced *multiple times from different threat models* — was the highest-signal finding. Six agents independently flagging silent exception handlers is not coincidence; it's the same bug class seen through six different lenses.

### Institutional residue

Rules 44-53 were born from this audit. Each rule is a compressed specification of "if you had run agent N's audit, here's what you would have found." The rules now run preventatively — every PR triggers a subset of the audit logic automatically.

**The engineering leadership lesson:** adversarial scoping beats exhaustive scanning. You don't audit "everything"; you audit specific threat models in parallel and triangulate on categorical findings.

---

## 3. The Canonical Fee Model: Three Scripts, Three Wrong Rates

**Date:** Pre-S3 · **Stakes:** Every backtest result since system inception · **Impact:** Retroactive invalidation of ~200 tests

During a routine research review, I noticed the backtest-A and backtest-B fee outputs disagreed on the same trade. Both scripts computed fees. Both produced different numbers. Neither matched production.

### The audit

Every fee computation in the codebase was grepped. Three distinct rate tables were in use:

```python
# Script A:   taker = 0.0005    # stale VIP-3 rate from 2023
# Script B:   taker = 0.00035   # copied from Binance, not HL
# Script C:   taker = 0.00045   # correct VIP-0
```

Every existing backtest was using one of these three models. Which one depended on which script the researcher had copied from three months earlier. The maker rates were similarly fragmented. None of them correctly credited the zero-fee leverage-change API — which is structurally important for Hyperliquid strategy design, since rebalances don't pay taker fees.

### The realization

Ad-hoc fee constants had colonized the codebase. No single script was "wrong" in a way anyone would call a bug — they were just each a local best-effort estimate frozen at a different moment. The system-level bug was **the absence of a canonical source of truth.**

### The fix

`src/backtesting/fee_model.py` became the sole authority for VIP-0 rates (4.5 bps taker, 1.5 bps maker). Every backtest, every test, every research script now imports from this module. Hardcoded fee rates are banned by Rule 37 and grep-enforced in CI.

The model itself became smarter: it correctly applies zero-fee to `update_leverage` and `update_isolated_margin` calls, which Hyperliquid clears without taker fees. This was a real structural insight — at 4.5 bps taker, rebalancing every 4h would cost ~10% annualized if leverage changes were charged. Because they aren't, intelligent rebalancing is *free*.

### Institutional residue

- Rule 37: canonical fee model only; hardcoded rates banned.
- All 200+ historical backtests were re-flagged as "fee model unknown" until rerun through the canonical model.
- The pattern generalized into a design principle: **any parameter that can be copied-and-frozen across scripts is a latent consistency bug.** Rates, thresholds, config defaults, and coin universes all got single-source-of-truth modules as a direct consequence.

**What this reveals about engineering maturity:** the bug here isn't the wrong rates. The bug is the architecture that permitted three different rates to coexist undetected for months. Fixing the rates without fixing the architecture just resets the clock on the next drift.

---

## 4. `pct_change` vs `change_pct`: The Silent Pipeline No-Op

**Date:** S3.x · **Stakes:** The recalibrator was effectively not running · **Duration undetected:** ~3 weeks

The leverage recalibrator had a clean interface. It produced a `RecalibrationResult` dataclass. The orchestrator consumed that result. Tests passed. Production logged "recalibration complete." Nothing worked.

### The bug

```python
# recalibrator produced:
class RecalibrationResult:
    change_pct: Decimal    # <-- name used here
    sleeve_name: str

# orchestrator consumed:
for result in results:
    if abs(result.pct_change) > threshold:   # <-- different name
        ...
```

The consumer read `result.pct_change`. Python raised `AttributeError`. The caller wrapped the iteration in `try/except Exception: pass`. Nothing propagated. The threshold check always failed, so no sleeve ever recalibrated.

For 3 weeks, every sleeve in production was running with the parameter values from the day the bug was introduced. The system appeared to be self-tuning. It was silently frozen.

### The detection

One of the 15-audit agents was hunting `except Exception: pass` — and this swallowed AttributeError was in its haul. Reading upstream to find what the exception was hiding revealed the silent name mismatch.

### The deeper problem

Typed dataclasses don't help here. Both producer and consumer were "internally correct" — each consistent with its own local naming. There was no compile-time check, no test, and no runtime signal. The interface contract was an attribute name, and Python treated a typo as a distinct identity.

### The fix

1. Rename to match (trivial).
2. **Interface contract tests** for every cross-component boundary (Rule 44):

```python
def test_recalibrator_output_shape():
    result = recalibrator.compute(...)
    # These names are what the orchestrator reads
    assert hasattr(result, 'pct_change')
    assert hasattr(result, 'sleeve_name')
```

These tests assert attribute presence, not just type. They run whenever the producer or the consumer changes. A rename that doesn't update the consumer now fails a test rather than silently breaking production.

### Institutional residue

- Rule 44: every cross-component attribute access needs a contract test on the consuming side.
- Rule 45: no silent exception swallowing. The bug would have surfaced immediately if the AttributeError had been logged.
- A new category of test file: `tests/contracts/*` — specifically for interface conformance across components, independent of the producer's own unit tests.

**The generalized insight:** dynamic typing makes attribute-name bugs invisible. The fix is not "use more types" — the fix is "test the shape of the boundary." This principle now applies to every producer/consumer pair in the system.

---

## 5. The 17x Equity Lie: When Internal State and Exchange State Diverge

**Date:** S4 live deployment · **Stakes:** Sizing decisions based on phantom capital · **Impact:** 4-sleeve capital ghost

The system deployed to mainnet on April 4. Three days later, a sanity check revealed BTC's internal `allocated_capital` of $4,616 while the actual HL cross-margin for BTC was $272. **17x discrepancy.** Not a display bug — the sizing logic was using the internal value.

### Root cause

Sleeve equity was computed from config weights:

```python
allocated_capital = config.weight * leverage * total_portfolio_equity
```

This formula describes what sleeve equity *should* be according to the config. It had **zero relationship to what the exchange had actually allocated.** When positions didn't enter, or when leverage recalibrated, or when the hedge book ate into margin, internal state and exchange state drifted apart. The system kept sizing against a fiction.

### Why this was not caught earlier

Paper-mode backtests pass with this formula because paper mode *is* the formula — there's no independent exchange state to disagree with. The backtest engine computes equity the same way production does, so the two agree by construction. The bug only surfaces when a real exchange becomes part of the loop.

### The fix

Sleeve equity now reads from `adapter.get_user_state()` — the authoritative exchange view. Config weights become *targets*, not facts. The sizer compares target-vs-actual and adjusts, but never treats config-derived numbers as ground truth.

Data plane verification (Rules 58-62) formalized the discipline:

- **58:** Production code paths read from authoritative exchange state, never from config projections, for anything that affects sizing or risk.
- **59:** When the exchange has multiple clearing houses (Hyperliquid has 3: standard perps, builder perps, spot), query all of them before reconciling.
- **60:** On restart, reconcile internal state against exchange state. Log any divergence. Block trading if divergence exceeds threshold.
- **61:** Data plane facts (positions, margins, funding rates) require freshness guards. Stale facts trigger explicit warnings.
- **62:** The reconciliation pass runs every N minutes in production and writes to a health endpoint.

### Related finding: builder perps were invisible

`get_all_positions()` defaulted to the standard clearing house. Builder perps (`km:NVDA`, `km:RTX`, `xyz:CL`) live in a separate clearing house and were literally not in the result set. For a period, the orchestrator believed it had zero exposure in those sleeves while real positions sat in a different subsystem of the exchange. Rule 59 was born the day that was found.

### Institutional residue

Data plane verification is now a first-class concern with its own test class, its own daemon, its own health-check endpoint, and five dedicated engineering rules. The principle: **"what the system thinks is happening" and "what is actually happening" are independent facts that must be mechanically reconciled.**

**Engineering leadership takeaway:** paper-mode testing and live-mode testing have structurally different failure modes. A system that passes every paper test can still have never-exercised code paths that only execute under real exchange state. Rules 58-62 institutionalized the discovery by forcing every state-bearing component to explicitly answer the question "how do I know this is still true?"

---

## 6. The Edge Is in the Exit, Not the Entry: VH-172

**Date:** S3.x research campaign · **Stakes:** Entire research priority · **Counterintuitive finding:** One of the most important

This is not a bug story. It's an epistemic story — the moment a research program discovered its own priorities were backwards.

### The common assumption

Algo trading research almost always focuses on entry signals. Crossovers, momentum, funding-rate spikes, smart-money positioning. Papers and hedge fund whitepapers are full of entry-signal innovation. The implicit model: if you could predict direction better, you would win more.

### The test

VH-172 was a hypothesis about a specific entry signal — smart-money positioning blended with dual-EMA crossover. The test was supposed to measure: does SM-blended entry beat vanilla dual-EMA?

Instead, the audit compared dual-EMA alone (vanilla) to dual-EMA + A1 trade management (asymmetric stops, breakeven triggers, conviction-erosion exits, time stops). On the same entry signal.

The finding, holding entry signal constant:

- **Dual-EMA + market exits:** cumulative return −39.7%.
- **Dual-EMA + A1 management:** cumulative return +25,330%.

*Same signal.* Same direction calls. The only difference was how positions were *managed after entry.*

Meanwhile: the t-statistics on dual-EMA entry signals across all 11 sleeves were statistically insignificant. The EMA crossover had essentially no alpha on entry. The entire directional alpha was being captured — or destroyed — in the exit.

### The inversion

Every future research priority was inverted the day VH-172's audit concluded. The hypothesis registry shifted from "new entry signals" to "exit management research." A1 trail parameters, progressive trail schedules, regime-aware trail factors, time stops, partial-close thresholds. The marginal Sortino improvement from entry-signal work is orders of magnitude smaller than the marginal improvement from exit-management work.

### Why it matters

The system's apparent profitability was almost entirely *preservation of profitable trades*, not *selection of profitable entries*. This is the opposite of the intuition most trading systems are built on, and it inverted the entire research program.

### Institutional residue

- Rule 39 (per-asset decomposition) applies to *exit parameters*, not just entry parameters. ATR stop widths, breakeven thresholds, and trail decay rates are all per-asset.
- New pitfall in `AGENT_PITFALLS.md`: "The #1 mistake future agents will make is spending 90% of their effort on entry signal IC when A1 management is the actual profit engine."
- Research backlog prioritization now starts with a gate: "is this an entry-signal hypothesis or an exit-management hypothesis?" Exit-management work is ranked higher by default.

**What this reveals about epistemic rigor:** the point of research isn't to confirm the plan. It's to be willing to throw the plan out when the data says the plan is wrong. VH-172 was set up to test one thing and ended up rewriting the research priorities. That outcome only happens if the research framework has room for it.

---

## 7. The Authority Conflict Map: Who Wins When Two Policies Disagree?

**Date:** 2026-04-18 audit · **Stakes:** Silent policy divergence · **Output:** 11-pair precedence mapping

As the system matured, more independent policies began influencing a single sizing decision: S4 target pipeline, Option C momentum sizer, TailRiskOverlay, EventEngine, Portfolio Exposure Governor, ModeManager, vol-drift recalibrator. Each is correct in isolation. The question nobody was asking: **when two of them disagree, who wins?**

### The audit

I mapped every pairwise authority relationship in the sizing pipeline. 11 authority pairs. For each, I answered: who wins, under what conditions, is this documented, what's the risk of divergence?

Selected findings:

| A | B | Who wins | Documented? | Risk |
|---|---|----------|-------------|------|
| S4TargetPipeline | TailRiskOverlay | S4 (silently overrides tail_mult) | Partially | **HIGH** — tail-risk logs show 0.5x reduction, but actual order uses full S4 size |
| S4TargetPipeline | EventEngine dead zone | S4 (silently overrides 0.9x) | **Undocumented** | HIGH |
| ModeManager (orchestrator) | ModeManager (S4) | **Both exist independently** | **Undocumented bug** | HIGH — silent state divergence |
| PortfolioGovernor | S4TargetPipeline | Governor feeds ephemeral cap | Yes | MED — ephemeral-ness not tested |

### The dual-ModeManager bug

The most alarming finding: two independent `ModeManager` instances existed — one in the orchestrator, one inside S4. Each had its own hysteresis timer, its own SAFE-mode state, its own lockout logic. If one instance said SAFE and the other said NORMAL, the system's behavior was defined by *whichever instance got called last*. No test would catch this because each instance was individually correct.

This was not a bug caused by a bad commit. It was the predictable consequence of two subsystems both needing mode awareness and each instantiating their own. Without an authority map, the duplication was invisible.

### The fix pattern (emerging, not yet complete)

1. Single source of truth for mode state. Orchestrator owns it; S4 reads it.
2. Explicit logging at every authority boundary: "Authority A would have said X, Authority B won, final decision Y."
3. **Contract test for the boundary itself** — assert that after a heartbeat, both ModeManager reads agree.

### Institutional residue

The authority conflict audit (`docs/AUTHORITY_CONFLICT_AUDIT_20260418.md`) became a recurring artifact. Any new sizing component must register in the authority map with its precedence relationships before it can be merged. This is not a style rule — it prevents the class of bug where a perfectly correct local policy produces globally incoherent behavior.

**What this demonstrates:** maturity in system design is not the absence of bugs. It is the ability to notice when two correct things compose into one wrong thing — and to institutionalize the check so it doesn't happen again.

---

## 8. L3 Silently Dead: Five Components Producing Nothing

**Date:** S4 cutover audit · **Stakes:** Hierarchical sizing was a no-op · **Duration undetected:** ~4 weeks

When S4 target sizing came online (2026-04-08), it replaced the Option C sizing hierarchy. Or, more precisely: it *bypassed* it. The `_s4_has_targets` gate caused three major L3 components — `MomentumSizer`, `VaultConsensusOverlay`, `SmartMoneySizing` — to exit early without contributing. `TailRiskOverlay` was never wired into the production config's `overlays` list, so it always returned 1.0x. The event engine's dead-zone multiplier computed, logged, then got overwritten by the S4 target override.

**5 of 6 L3 sizing components were producing nothing for 4 weeks. The architecture diagram said they existed. The code said they existed. The logs said they existed. But the final sizing output was unaffected by any of them.**

### How it went undetected

Each component's unit tests passed. Each component's integration test mocked the S4 path out. Each component's logs showed expected outputs. The bug was not that any component was broken — the bug was that **the product of a correct orchestrator and five correct overlays was a silent bypass.**

The tests weren't wrong. They were scoped to the wrong question. Each test asked "does this component work?" when the question that mattered was "does this component's output reach the order?"

### Detection

A routine sizing audit in preparation for the S4 closure milestone. "Why is the executed size equal to the S4 raw target with no intermediate adjustment?" The trace followed the value through the stack and found every overlay either gated out or overwritten downstream.

### The fix (in progress)

- Log the actual adjustment at every layer: not "TailRiskOverlay computed 0.7x" but "TailRiskOverlay 0.7x was applied" vs "TailRiskOverlay 0.7x was DISCARDED by S4 override."
- End-to-end sizing traces in tests: inject a known input, assert the final order size reflects the expected stack of multipliers.
- Layered tests moved from unit-scope to full-pipeline-scope for the sizing chain specifically.

### Institutional residue

This bug class has a name now: **observational silence** — the system observably does the right thing (logs say so) while functionally doing nothing. It's the sizing-pipeline version of `except Exception: pass`.

The defensive pattern: **every component must report not what it *computed*, but what it *caused*.** Logging intermediate values is not enough. Log the delta from before-this-component to after-this-component, and assert in tests that deltas match expectations at the pipeline level, not the component level.

---

## Meta: What These Stories Have in Common

Reading these eight stories in sequence, a pattern emerges. None of them was caught by conventional testing. Every one required a specific inversion of perspective:

- **Staleness (#1):** look for state that *should* decay but can't.
- **Adversarial audit (#2):** run multiple narrow threat models in parallel, triangulate on intersections.
- **Canonical sources (#3):** find parameters that copy-freeze across scripts.
- **Interface contracts (#4):** test the shape of boundaries, not just unit behavior.
- **Data plane (#5):** separate "what the system believes" from "what's actually true."
- **Epistemic rigor (#6):** let the data invalidate the research agenda, not just its hypotheses.
- **Authority composition (#7):** correct locally ≠ correct globally.
- **Observational silence (#8):** logs can lie by telling the truth about the wrong thing.

The institutional residue matters more than the individual fixes. The fixes are four-line diffs. The residue is 20+ rules, a contract-test category, a data-plane verification daemon, an authority map that gates new PRs, and an explicit taxonomy of bug classes. That residue is the actual deliverable of operating a production trading system with rigor.

The 62-rule agent contract, 21 VRULEs, and 127-hypothesis registry are not overhead on top of the code. They *are* the engineering leadership output. The code is what got written after the rules were clear.

---

*For broader context on how this infrastructure is operated by AI agents, see [AI_DEVELOPMENT.md](AI_DEVELOPMENT.md). For the research methodology that produced VRULEs and the hypothesis registry, see [METHODOLOGY.md](METHODOLOGY.md).*

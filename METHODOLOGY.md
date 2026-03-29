# VALEN Research Methodology

## Philosophy

Every design decision in VALEN is treated as a hypothesis to be tested, not an opinion to be defended. This methodology was forged through EISEN's development (7 system versions, 4 strategy eliminations, hundreds of backtests) and hardened through VALEN's own research program: **81 hypotheses tested, 21 dead-end verdicts, 900+ backtests** across 6 months.

The core principle: **a strategy that cannot be killed by its own test plan is not being tested rigorously enough.**

The second principle: **a well-documented rejection is more valuable than an untested assumption.** VALEN's 21 VRULEs (dead-end verdicts) prevent future work from repeating past failures. Each VRULE encodes not just "this doesn't work" but the specific conditions under which it was tested, so it can be re-evaluated if conditions change.

---

## Hypothesis-Driven Development

Every proposed change — new signal, parameter adjustment, sleeve addition — follows a formal lifecycle:

```
┌──────────────┐
│  Hypothesis   │  Falsifiable statement with measurable prediction
└──────┬───────┘
       ▼
┌──────────────┐
│  Test Plan    │  Dataset, timeframe, metrics, statistical tests, sample size
└──────┬───────┘
       ▼
┌──────────────┐
│ Kill Criteria │  Pre-defined thresholds that trigger elimination
└──────┬───────┘
       ▼
┌──────────────┐
│  Execution    │  Backtest campaign with factorial parameter sweep
└──────┬───────┘
       ▼
┌──────────────┐
│  Red Team     │  Regime analysis, lookahead check, data snooping audit
└──────┬───────┘
       ▼
┌──────────────┐
│   Verdict     │  Accept, reject, or modify — with evidence
└──────────────┘
```

### Hypothesis Registry

All 81 hypotheses are tracked in a central JSON registry with:
- Unique ID (e.g., `VH-087`)
- Status: `proposed` | `testing` | `accepted` | `rejected` | `conditional_pass`
- Parent hypothesis (if derived from a prior test)
- Kill criteria (quantitative thresholds)
- Test results (metrics, dataset provenance, timestamp)
- Verdict rationale with supporting data

This creates an auditable trail. Any current parameter can be traced back to the hypothesis that justified it.

---

## Factorial Campaign Design

Parameter optimization uses factorial sweeps rather than random search or Bayesian optimization. This captures interaction effects between parameters — a critical requirement discovered when 6 individually-accepted findings produced worse results when combined.

### Process

1. **Identify factors**: Select 3-5 parameters to sweep
2. **Define levels**: 2-4 levels per factor, chosen based on domain knowledge
3. **Full factorial**: Run all combinations (e.g., 4 x 3 x 3 x 2 = 72 backtests)
4. **Analyze main effects**: Which factors dominate performance?
5. **Analyze interactions**: Do any factor pairs have non-additive effects?
6. **Select robust region**: Choose parameters in a broad performance plateau, not the single best point

### Why Not Bayesian Optimization?

Bayesian optimization finds the single best point efficiently. But in trading, the single best point is almost always overfit. We want the **broad plateau** — a region of parameter space where performance is consistently good. Factorial design reveals the shape of the response surface, which is more valuable than the peak.

### Why Factorial Interaction Testing Is Mandatory

**Rule 31 exists because of a specific failure.** Six independently-validated findings (each improving Sortino in isolation) were combined and produced results *worse* than the baseline. The reason: negative interaction effects between findings that were invisible in isolation.

The rule now requires pairwise testing of every combination of 2+ accepted findings before simultaneous deployment. This is expensive (combinatorial) but prevents the assumption that independent improvements compose additively.

---

## Temporal Red-Teaming

After every factorial campaign, results are challenged through 5 temporal analyses:

### 1. Regime Decomposition
Split the test period into regimes (bull, bear, sideways, high-vol, low-vol, crash+recovery) and evaluate performance in each. A strategy that only works in one regime is fragile.

### 2. Rolling Window Analysis
Run the backtest on rolling 90-day windows. Plot Sortino over time. Look for:
- Monotonic decay (alpha erosion)
- Regime-dependent clustering
- Sudden regime breaks

### 3. Out-of-Sample Validation
The test dataset is always split:
- **In-sample (IS)**: 70% — used for parameter selection
- **Out-of-sample (OOS)**: 30% — held out, never used for optimization
- **IS/OOS ratio**: If OOS Sortino < 50% of IS Sortino, the strategy is likely overfit

### 4. Lookahead Bias Audit
Systematic check for:
- Future data leaking into signal computation
- Close prices used for entry decisions (should use open of next bar)
- Funding rate applied before settlement time

### 5. Data Snooping Audit
If N parameter combinations were tested, apply a data snooping correction:
- Report the probability that the best result is due to chance
- Use Bonferroni correction as the minimum bar (331K observation tests use this)

---

## Dead-End Verdicts (VRULEs)

Failed strategies and rejected hypotheses receive formal verdicts. VALEN has 21 VRULEs, each preventing future work from repeating a tested failure.

### VRULE Structure

Each verdict includes:
- **Scope**: Component-level or system-level
- **Finding**: What was tested and what happened
- **Evidence**: Specific metrics, sample sizes, test conditions
- **Conditions for re-evaluation**: When this verdict might be overturned

### Selected VRULEs

| VRULE | Finding | Why It Matters |
|-------|---------|---------------|
| VRULE-001 | Dynamic leverage per regime is dead | Prevents revisiting leverage-switching schemes |
| VRULE-012 | Strategy-mode engines lose to dual-EMA | Prevents building complex switching logic |
| VRULE-013 | Cross-exchange derivatives: zero alpha for BTC | Prevents Coinalyze OI/funding signal work |
| VRULE-019 | Naked shorts liquidated in bull markets | Requires 3-tier loss management for all shorts |
| VRULE-020 | Funding is per-asset (original model 16x wrong) | Corrected fee model; PAXG funding = income |
| VRULE-021 | Mean reversion sideways loses to holding | Prevents MR-in-sideways strategy proposals |

### VRULE Quality Control

A key lesson: **premature VRULEs waste more time than premature acceptance.** VRULE-017 (CEM rejection) was declared based on testing with dead signals, BTC-only data, and wrong fee accounting. When overturned, weeks of work had been skipped based on an invalid verdict.

Every VRULE now requires surviving an adversarial review (Rule 40):
1. Was the test on the right data?
2. The right assets (multi-asset, not BTC-only)?
3. The right fee model (canonical, not hardcoded)?
4. The right signals (verified non-zero hit rate)?

---

## Optimization Target Selection

### Why Sortino Over Sharpe

The Sharpe ratio penalizes upside volatility equally with downside volatility. In crypto, a strategy capturing 40% upside moves while limiting drawdowns to 8% has high total volatility but excellent risk-adjusted returns. Sharpe penalizes it. Sortino rewards it.

This is not a preference — it changes which parameter sets survive optimization. The gamma=2 parameter in Sortino applies quadratic penalty to downside deviation, making the metric more sensitive to tail risk.

| Priority | Metric | Rationale |
|----------|--------|-----------|
| Primary | **Sortino(gamma=2)** | Penalizes only downside; upside vol is desirable in crypto |
| Secondary | **Omega(threshold=0)** | Full-distribution, probability-weighted gain/loss ratio |
| Tertiary | **Calmar** | Return / max drawdown — the survival metric |
| **Never** | **Sharpe** | Penalizes upside volatility; structurally wrong for right-skewed returns |

### The Per-Asset Decomposition Finding

The single strongest meta-finding across all VALEN research: **per-asset signal decomposition improved Portfolio Sortino by +123%** compared to aggregate signals.

Every signal, threshold, modulation frequency, and stop width performs better when calibrated per-asset:

| Dimension | Aggregate (old) | Per-asset (current) |
|-----------|----------------|-------------------|
| Vol modulation | Portfolio-level vol | Per-sleeve vol regime |
| Short basket | Aggregate activation | Per-coin momentum/funding/OI |
| Stops | Fixed 1.5% for all | ATR-scaled (HYPE 2.0x, PAXG 3.0x) |
| Modulation frequency | Uniform 4h | Per-asset (BTC 1h, HYPE 15m, PAXG 4h) |
| Recalibration | Portfolio-wide grid | Per-sleeve parameter sweeps |

This finding is encoded as Rule 39: every new mechanism must ask "Does this use an aggregate signal where a per-asset signal would be more precise?"

---

## Adversarial Signal Audit

Before any new signal is added, it undergoes an adversarial audit:

1. **What is the economic mechanism?** If you cannot explain why this signal predicts returns, it is curve-fitting.
2. **Who is on the other side?** Every profitable trade has a counterparty. Who are they and why are they wrong?
3. **What regime does this signal fail in?** If you cannot identify the failure mode, you have not looked hard enough.
4. **Is this signal crowded?** Evidence for/against crowding.
5. **What is the signal's half-life?** How long before this edge erodes.
6. **What is the recent hit rate?** Signals with <5% activation on recent 30-day data are suspect. The funding signal (0/73 hit rate) should have been caught at the wiring stage, not months later.

---

## Frequency Audit

Before any backtest, a frequency audit ensures data granularity matches the strategy's decision frequency. This prevents a catastrophic error: **optimizing a 4h strategy on 1h data** (which overfits to intrabar noise the strategy cannot trade).

The audit checks:
- Signal computation frequency vs. candle interval
- Minimum data points for indicator warm-up
- Information loss percentage (signals computed on bars the strategy cannot act on)

A frequency mismatch above 90% information loss blocks the backtest from running.

**Why this exists**: VALEN's most important research finding is that ALL candle-based directional signals collapse at sub-hourly frequencies. Fee drag exceeds 100% of gross alpha at VIP-0. Without the frequency audit, researchers repeatedly test sub-hourly signals, get promising in-sample results (from overfitting to noise), and waste time on fundamentally unviable strategies.

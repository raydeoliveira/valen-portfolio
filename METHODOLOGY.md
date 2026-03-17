# VALEN Research Methodology

## Philosophy

Every strategy decision in VALEN is treated as a hypothesis to be tested, not an opinion to be defended. This methodology was forged through EISEN's development (7 system versions, 4 pillar eliminations, hundreds of backtests) and carried forward into VALEN with refinements.

The core principle: **a strategy that cannot be killed by its own test plan is not being tested rigorously enough.**

---

## Hypothesis-Driven Development

Every proposed change — new signal, parameter adjustment, pillar addition — follows a formal lifecycle:

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

All hypotheses are tracked in a central JSON registry with:
- Unique ID (e.g., `HYP-P2-003`)
- Status: `proposed` | `testing` | `accepted` | `rejected` | `modified`
- Parent hypothesis (if derived from a prior test)
- Kill criteria (quantitative thresholds)
- Test results (metrics, dataset hash, timestamp)
- Verdict rationale

This creates an auditable trail. You can trace any current parameter back to the hypothesis that justified it.

### Example Hypothesis

```
ID:         HYP-P2-007
Statement:  "P2 Short Hedge generates positive Sortino(γ=2) > 0.5 on BTC perps
             during bear regimes (drawdown > 15% from local high) using RSI + EMA
             crossover confirmation, with 3x leverage and 2% max position size."
Kill:       Sortino < 0.3 OOS, or max drawdown > 25%, or win rate < 35%
Dataset:    BTC 1h candles, 2023-01-01 to 2025-06-30, HL archive
Status:     testing
```

---

## Factorial Campaign Design

Parameter optimization uses factorial sweeps rather than random search or grid search on individual parameters. This captures interaction effects between parameters.

### Process

1. **Identify factors**: Select 3-5 parameters to sweep (e.g., EMA period, RSI threshold, leverage, position size)
2. **Define levels**: 2-4 levels per factor, chosen based on domain knowledge
3. **Full factorial**: Run all combinations (e.g., 4 x 3 x 3 x 2 = 72 backtests)
4. **Analyze main effects**: Which factors dominate performance?
5. **Analyze interactions**: Do any factor pairs have non-additive effects?
6. **Select robust region**: Choose parameters in a broad performance plateau, not the single best point

### Why Not Bayesian Optimization?

Bayesian optimization finds the single best point efficiently. But in trading, the single best point is almost always overfit. We want the **broad plateau** — a region of parameter space where performance is consistently good, not a narrow spike. Factorial design reveals the shape of the response surface, which is more valuable than the peak.

---

## Temporal Red-Teaming

After every factorial campaign, results are challenged through temporal analysis:

### 1. Regime Decomposition
Split the test period into regimes (bull, bear, sideways, high-vol, low-vol) and evaluate performance in each. A strategy that only works in one regime is fragile.

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
- Use White's Reality Check or Hansen's SPA test for formal statistical assessment

---

## Dead-End Documentation

Failed strategies and rejected hypotheses are documented with the same rigor as successes. This serves two purposes:

1. **Prevent repetition**: Future researchers (human or AI) can see why an approach was tried and why it failed
2. **Enable re-evaluation**: When structural conditions change (e.g., moving from Coinbase to Hyperliquid), dead-ends can be systematically re-evaluated

### Dead-End Classification

Each eliminated strategy or hypothesis receives a classification:

| Class | Meaning | Re-evaluate? |
|-------|---------|--------------|
| **Structural** | Failed due to exchange-specific constraints (fees, instruments) | Yes, on new exchange |
| **Fundamental** | No alpha exists in the signal | No |
| **Temporal** | Alpha existed but decayed | Maybe, with regime analysis |
| **Implementation** | Idea sound but execution flawed | Yes, with better implementation |

### EISEN-to-VALEN Re-evaluation

Three EISEN eliminations were classified as **Structural** and re-evaluated for VALEN:

- **P2 Short Hedge** (EISEN: eliminated) — Failed due to Coinbase futures fee drag. Hyperliquid has native perp shorts at lower fees. **Re-evaluation: viable.**
- **P3 Grid** (EISEN: eliminated) — Failed due to no maker rebates on Coinbase. Hyperliquid offers maker fee advantages. **Re-evaluation: viable.**
- **P5 Momentum** (EISEN: eliminated, -38.85% forward) — Failed due to spot-only, long-only constraints. Hyperliquid offers 100+ perp markets with short-side. **Re-evaluation: viable with short-side.**

---

## Optimization Target Selection

### Why Sortino Over Sharpe

This is not a preference — it is a mathematical argument.

The Sharpe ratio is defined as:

```
Sharpe = (R - Rf) / σ
```

Where σ is total standard deviation (upside + downside). This penalizes strategies with high upside volatility — exactly the strategies we want in crypto.

The Sortino ratio is defined as:

```
Sortino = (R - MAR) / σ_downside
```

Where σ_downside only counts returns below the minimum acceptable return (MAR). A strategy that captures large upside moves while limiting drawdowns has high Sortino and mediocre Sharpe. We optimize for Sortino.

The gamma parameter (γ=2) in our Sortino calculation applies quadratic penalty to downside deviation, making the metric more sensitive to tail risk.

### Why Omega as Secondary

The Omega ratio considers the entire return distribution, not just mean and variance:

```
Omega(θ) = ∫[θ,∞] (1 - F(r)) dr / ∫[-∞,θ] F(r) dr
```

With θ=0, this gives the probability-weighted ratio of gains to losses. It captures skewness and kurtosis that Sortino misses.

### Why Calmar as Tertiary

```
Calmar = Annualized Return / Max Drawdown
```

Calmar is the "survival metric." A strategy with excellent Sortino but 60% max drawdown will blow up before the long run arrives. Calmar keeps us honest about drawdown risk.

### STARR for Leverage

```
STARR = Sortino / Average Realized Risk
```

When running leveraged perp positions, the Sortino alone doesn't capture the risk amplification. STARR adjusts for the actual risk taken, making it possible to compare a 3x leveraged strategy with a 1x strategy on equal footing.

---

## Adversarial Signal Audit

Before any new signal or indicator is added to a strategy, it undergoes an adversarial audit:

### Questions the Audit Answers

1. **What is the economic mechanism?** If you cannot explain why this signal should predict returns, it is curve-fitting.
2. **Who is on the other side?** Every profitable trade has a counterparty losing money. Who are they and why are they wrong?
3. **What regime does this signal fail in?** Every signal has a failure mode. If you cannot identify it, you have not looked hard enough.
4. **Is this signal already crowded?** If many participants use the same signal, it is arbitraged away. What is the evidence for or against crowding?
5. **What is the signal's half-life?** Signals decay. How long before this edge erodes?

### Game-Theoretic Framing

Trading is adversarial. The market is not a random number generator — it is populated by other agents with their own models. A signal that works in backtest may fail live because:

- Other participants adapt to the same signal
- The signal's alpha was absorbed into market microstructure
- Regime change invalidates the economic mechanism

The adversarial audit forces explicit reasoning about these dynamics before committing to implementation.

---

## Frequency Audit

Before any backtest or parameter sweep, a frequency audit ensures the data granularity matches the strategy's decision frequency. This prevents a common and catastrophic error: **optimizing a daily strategy on hourly data** (which overfits to intraday noise that the strategy cannot trade).

The audit checks:
- Signal computation frequency vs. candle interval
- Minimum data points required for indicator warm-up
- Information loss percentage (signals computed on data the strategy cannot act on)
- Recommended adjustments if mismatch is detected

A frequency mismatch above 90% information loss blocks the backtest from running.

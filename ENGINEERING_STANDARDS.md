# VALEN Engineering Standards

## Code Style

### Python
- Python 3.11+ required
- Modern syntax: `X | Y` union types, `match` statements, f-strings
- Full type annotations on all function signatures
- `mypy --strict` must pass with zero errors
- `ruff` with comprehensive rule set (Black-compatible, 88 char lines)
- **No `print()` statements** — all output through structured logger

### Financial Values
- `Decimal` for all monetary amounts, prices, and rates — never `float`
- This is enforced in code review. A `float` representing money is a bug.

---

## Architecture Rules

### Import Boundaries (CI-Enforced)

```
Domain  →  (nothing — domain is pure)
Ports   →  Domain only
Services →  Ports + Domain (never Adapters directly)
Adapters →  Ports + Domain (implements port interfaces)
Scripts  →  Anything (entry points)
Tests   →  Anything (testing boundary)
```

**These are checked programmatically, not by convention.** A single import violation fails CI. This is what makes Clean Architecture actually clean — the constraints are mechanical, not aspirational.

### Domain Model Rules
- All models use Pydantic v2 `BaseModel`
- Exchange-agnostic — no Hyperliquid-specific types in domain
- `Decimal` for all financial values
- Enums for fixed vocabularies (`Direction`, `OrderSide`, `OrderType`, `TimeInForce`)

### Port Design
- Ports are abstract base classes (ABCs)
- Every port method has a docstring with Args, Returns, and behavioral notes
- Ports define contracts with zero implementation logic
- New port methods require contract tests

### Adapter Rules
- Each adapter implements exactly one port
- Adapters handle exchange-specific translation (SDK types → domain types)
- Error handling lives in adapters, not in domain or services
- Adapters never expose exchange SDK types to consumers

---

## Rules That Exist Because of Bugs

These engineering standards were not designed in advance. Each one was added after a specific production incident. The incident is documented so the rule can be understood, not just followed.

### No Silent Exception Swallowing (Rule 45)

```python
# BANNED — hides bugs for weeks
except Exception:
    pass

# REQUIRED — at minimum, log
except Exception as exc:
    logger.warning("Operation failed: %s", exc)
```

**Incident**: The recalibrator was completely dead for an entire development session because an `AttributeError` (wrong attribute name) was caught by a bare `except Exception: pass`. Four other components had the same pattern, all hiding real bugs.

### `default_factory` Must Be Pure (Rule 46)

```python
# BANNED — makes tests non-deterministic, breaks CI
@dataclass
class Config:
    limits: dict = field(default_factory=fetch_from_api)

# REQUIRED — static defaults
@dataclass
class Config:
    limits: dict = field(default_factory=dict)
```

**Incident**: `GovernorConfig(default_factory=fetch_hl_leverage_limits)` made network calls during dataclass construction, breaking CI and making tests non-deterministic.

### Interface Contract Verification (Rule 44)

```python
# REQUIRED — every cross-component attribute access needs a test
def test_recalibrator_output_matches_orchestrator_input():
    result = recalibrator.compute(...)
    assert hasattr(result, 'pct_change')  # orchestrator reads this
    assert hasattr(result, 'sleeve_name')  # orchestrator reads this
```

**Incident**: The recalibrator produced `change_pct` but the orchestrator consumed `pct_change`. The silent mismatch (caught by bare except) meant the entire recalibration pipeline was a no-op.

### State Persistence Round-Trip Tests (Rule 52)

```python
# REQUIRED — every save/load cycle must be verified
def test_state_round_trip():
    original = SystemState(positions=[...], equity=10000, pnl_history=[...])
    save_state(original, path)
    restored = load_state(path)
    assert restored.positions == original.positions
    assert restored.equity == original.equity
    assert restored.pnl_history == original.pnl_history
```

**Incident**: Three critical fields were written by `save_state()` but ignored by `load_state()`. On restart: positions wiped, equity reset to default, PnL history lost.

### Dead Code Audit Per PR (Rule 50)

**Incident**: 19 dead modules accumulated over weeks of development. Each session added code but never removed unused paths. Methods like `check_health()`, `destroy_trade_manager()`, and `remove_a1_manager()` were defined but never called — pure dead code giving false confidence in coverage.

### Candle Count Must Exceed Indicator Lookback (Rule 51)

**Incident**: RENDER's signal engine used a 500-bar regime EMA, but the candle fetch only requested 300 bars. The regime gate was always in a cold-start state, producing incorrect signals for weeks.

### Data Plane Verification (Rules 58-62)

**Incident**: After deploying to mainnet, internal equity tracking was 17x wrong because sleeve equity was computed from config weights instead of actual exchange margin allocations. Rules 58-62 enforce reconciliation between internal state and exchange-reported state at multiple checkpoints.

---

## Testing Standards

### Coverage Targets

| Layer | Target | Rationale |
|-------|--------|-----------|
| Domain models | 100% branch | Pure logic, no excuses |
| Port contracts | 100% method | Defines the system boundary |
| Services | >90% branch | Core business logic |
| Adapters | >80% | Network paths may be mocked |
| Interface contracts | 100% | #1 bug category |

### Testing Principles

1. **Strategy tests never touch the network.** All exchange interactions mocked through ports.
2. **Deterministic data.** Tests produce identical results every run.
3. **Test behavior, not implementation.** Assert on outputs and side effects.
4. **Interface contract tests for every cross-component boundary.** Verifies attribute names match.
5. **State round-trip tests for every persistent component.** save → load → assert equality.

### Canonical Fee Model in Tests

All backtests use `src/backtesting/fee_model.py`. Never hardcode fee rates in test scripts.

**Rule 37 incident**: Three different fee rates appeared in three different test scripts. All were wrong. The canonical model reflects VIP-0 tiers (4.5 bps taker, 1.5 bps maker) and correctly credits zero-fee leverage changes.

---

## Logging Standards

| Level | Use |
|-------|-----|
| DEBUG | Signal computation, rate limiter budget, indicator values |
| INFO | Trades, state changes, configuration loaded |
| WARNING | Degraded conditions, approaching limits, recovered errors |
| ERROR | Failures requiring attention |
| CRITICAL | Data loss, margin emergencies, liquidation proximity |

What NOT to log: raw API responses (secrets risk), full order book snapshots (volume), internal loop iterations without state changes.

---

## Configuration Management

1. **No hardcoded parameters.** Every threshold, period, and limit in config files.
2. **Pydantic validation at load time.** Invalid configs fail fast.
3. **Environment variables for secrets.** Wallet keys in `.env`, never in config.
4. **Atomic writes.** Config updates via tmp + rename to prevent partial writes.
5. **Per-sleeve configs.** No one-size-fits-all — each sleeve has independent configuration.
6. **109 config files** managed across sleeves, signal parameters, recalibration, and deployment.

---

## Change Hygiene

### Commit Convention
```
<type>(<scope>): <description>

Types: feat, fix, refactor, test, docs, infra, research
Scopes: btc, hype, short-basket, sor, backtest, governor, ...
```

### PR Requirements
1. Descriptive title and rationale
2. All tests passing (4,376 tests)
3. Architecture conformance check passing
4. Applied to longs: YES/NO. Applied to shorts: YES/NO. If NO, explain why not.
5. Dead code audit
6. Quantitative claims require verification numbers

### Quantitative Claims
Every quantitative claim requires a verification number:
- **Banned**: "significant improvement", "better performance", "reduced fees"
- **Required**: "+0.555 Sortino delta (1.09 → 1.645)", "$100.31/6mo (1% of equity)"

Unquantified claims are treated as unverified. This is Rule 35.

# VALEN Engineering Standards

## Code Style

### Python Version
- Python 3.11+ required
- Full use of modern syntax: `X | Y` union types, `match` statements, f-strings

### Type Hints
- All function signatures must have complete type annotations
- `mypy --strict` must pass with zero errors
- Use `from __future__ import annotations` for forward references
- Prefer `X | None` over `Optional[X]`

### Linting
- **ruff** with comprehensive rule set
- Line length: 88 characters (Black-compatible)
- Import sorting: isort-compatible via ruff

### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`
- Module-level: `lowercase_with_underscores`

---

## Architecture Rules

### Import Boundaries

These are enforced by CI, not by convention.

```
Domain  →  (nothing — domain is pure)
Ports   →  Domain only
Services →  Ports + Domain (never Adapters directly)
Adapters →  Ports + Domain (implements port interfaces)
Scripts  →  Anything (entry points)
Tests   →  Anything (testing boundary)
```

**Violation of import boundaries fails CI.**

### Domain Models
- All domain models use Pydantic v2 `BaseModel`
- Models are exchange-agnostic — no Hyperliquid-specific types in domain
- Use `Decimal` for all financial values (never `float`)
- Enums for fixed vocabularies (`Direction`, `OrderSide`, `OrderType`, `TimeInForce`)

### Port Design
- Ports are abstract base classes (ABCs)
- Every port method has a docstring with Args, Returns, and behavioral notes
- Ports define contracts — they never contain implementation logic
- New port methods require corresponding tests in the contract test suite

### Adapter Implementation
- Each adapter implements exactly one port
- Adapters handle exchange-specific translation (e.g., Hyperliquid SDK types to domain types)
- Error handling lives in adapters, not in domain or services
- Adapters never expose exchange SDK types to consumers

---

## Testing Requirements

### Coverage Targets
- Domain models: 100% branch coverage
- Port contracts: 100% method coverage
- Services: >90% branch coverage
- Adapters: >80% (network-dependent paths may be mocked)

### Test Organization
```
tests/
├── conftest.py              # Shared fixtures
├── test_domain_models.py    # Domain layer
├── test_ports.py            # Port contract verification
├── test_indicators.py       # Indicator math verification
├── test_backtest_engine.py  # Backtest mechanics
├── test_p1_btc_treasury.py  # Per-pillar strategy tests
├── test_p2_short_hedge.py
├── test_p3_grid_perp.py
├── test_p6_mean_reversion.py
├── test_rate_limiter.py     # Infrastructure
├── test_database.py
├── test_hl_adapter.py
├── test_monitor.py
└── ...
```

### Testing Principles
1. **Strategy tests never touch the network.** All exchange interactions are mocked through port interfaces.
2. **Use deterministic data.** Tests must produce identical results on every run. No random seeds without explicit control.
3. **Test behavior, not implementation.** Assert on outputs and side effects, not internal state.
4. **One assertion per concept.** A test with 15 assertions is 15 tests pretending to be one.
5. **Fixtures in conftest.py.** No duplicate test setup across files.

---

## Logging

### Rules
- **Never use `print()`.** All output goes through `src.services.logger`.
- Structured logging with consistent fields: `timestamp`, `level`, `module`, `message`, `context`
- Log levels: `DEBUG` for signal computation, `INFO` for trades and state changes, `WARNING` for degraded conditions, `ERROR` for failures, `CRITICAL` for data loss or margin emergencies

### What to Log
- Every order submission and fill
- Every signal computation result (at DEBUG)
- Configuration loaded at startup
- Rate limiter budget state (at DEBUG)
- Connection events (connect, disconnect, reconnect)

### What Not to Log
- Raw API responses (too verbose, potential secrets)
- Full order book snapshots (high volume, low signal)
- Internal loop iterations without state changes

---

## Configuration Management

### Principles
1. **No hardcoded parameters in strategy code.** All thresholds, periods, and limits come from configuration.
2. **Pydantic validation at load time.** Invalid configs fail fast with clear messages.
3. **Environment variables for secrets.** Wallet keys, API keys, and addresses live in `.env`, never in config files.
4. **Config versioning.** Every config change is tracked in git with a rationale in the commit message.

### Config Structure
```json
{
  "pillar": "P1",
  "name": "BTC Treasury",
  "enabled": true,
  "leverage": 3,
  "max_position_pct": 0.15,
  "indicators": { ... },
  "risk": {
    "max_drawdown_pct": 0.12,
    "stop_loss_pct": 0.05
  }
}
```

---

## Change Hygiene

### Commit Messages
```
<type>(<scope>): <description>

Types: feat, fix, refactor, test, docs, infra, research
Scopes: p1, p2, ..., p8, backtest, adapter, domain, ports, monitor, allocator, ci
```

### Pull Request Requirements
1. Descriptive title (not just the branch name)
2. Summary of changes and rationale
3. Test results (all passing)
4. Architecture check passing
5. Agent-ID if written by an AI agent

### Code Review Checklist
- [ ] Import boundaries respected
- [ ] No `float` for financial values
- [ ] No `print()` statements
- [ ] Type hints complete
- [ ] Tests cover new code paths
- [ ] Config changes validated
- [ ] No hardcoded parameters

---

## Golden Rules

1. **Verify before reporting.** Run `agent_verify.sh` before claiming work is done.
2. **Log every backtest.** Results go to `data/backtests/` — no exceptions.
3. **Use wrapper scripts.** Never ad-hoc when a script exists.
4. **One concern per edit.** Small, reviewable changes.
5. **Never modify data by hand.** Databases and logs are append-only.
6. **Never enable live trading without explicit approval.** Testnet first, always.
7. **Structured logging only.** `src.services.logger`, never `print()`.
8. **Specify scope for performance claims.** Pillar-level or system-level — they are different.
9. **No orphan scripts.** Every script is registered and documented.
10. **No structural anti-patterns.** Review these standards before writing logic.

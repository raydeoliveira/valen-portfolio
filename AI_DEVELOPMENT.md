# AI-Augmented Development

## Overview

VALEN was built and is continuously developed using **coordinated AI agents** operating in parallel sessions. This is not "AI-assisted coding" — it is a structured multi-agent system with defined isolation boundaries, coordination protocols, and an evolving rule set that grows from production incidents.

The result: **905+ PRs merged, 4,376 tests, 62 agent contract rules, 21 research verdicts** — a production system that is defined as much by its development process as by its trading logic.

---

## Scale

| Metric | Early (Month 1) | Current |
|--------|-----------------|---------|
| PRs merged | 18 | **905+** |
| Tests | 497 | **4,376** across 323 files |
| Agent contract rules | 10 | **62** |
| Data daemons | 0 | **28** |
| Research hypotheses | 0 | **81** |
| Dead-end verdicts (VRULEs) | 0 | **21** |
| Backtests logged | ~50 | **900+** |
| Config files | ~10 | **109** |
| System status | Paper trading | **Live on mainnet** |
| Deployment | Local daemons | **AWS EC2, systemd** |
| Development model | Sprint-based | Continuous parallel sessions |

The "Month 1" numbers reflect the initial wave-based sprint that built the foundation. The current numbers reflect continuous evolution — each session adding capability, discovering bugs, tightening rules, and killing bad ideas with evidence.

---

## Coordination Architecture

### Git Worktree Isolation

Each agent operates in its own git worktree, branched from `main`. This provides:
- **File-level isolation**: No two agents edit the same file simultaneously
- **Clean merge path**: Each agent's work is a self-contained branch
- **Failure isolation**: If one agent's work is rejected, others are unaffected

### Conflict Preflight (Mandatory)

Before picking up any work, agents run `conflict_preflight.sh` which checks for exclusive zone contention — overlapping file modifications in active branches. If exit code is 2, the agent STOPS. This prevents the cascading merge conflict problem that plagues naive parallel development.

### Merge Orchestrator

Before merging PRs, `merge_orchestrator.sh` computes safe merge ordering based on file dependency analysis. This replaced ad-hoc "merge and hope" which created integration failures when PRs touched shared interfaces.

### Verification Gate

Every PR must pass `agent_verify.sh` (lint + type check + tests + architecture conformance) before merge. The architecture check programmatically enforces import boundaries — domain models cannot import from adapters, services cannot import directly from adapters, etc.

---

## The 62-Rule Agent Contract

The agent contract is the most important artifact of the AI development process. It started with 10 basic rules and grew to 62 through a feedback loop: every production incident or research failure spawns a new rule that prevents recurrence.

### Rule Evolution Timeline

**Rules 1-10 (Foundation):** Basic hygiene — run verification before reporting, log backtests, use wrapper scripts, never enable live trading without approval.

**Rules 11-28 (Research discipline):** Added as research methodology matured — hypothesis registry, frequency audits, per-asset decomposition, terminology standardization, data tier isolation, Hyperliquid-specific constraints.

**Rules 29-38 (Research failure prevention):** Each rule prevents a specific failure that actually occurred:
- **Rule 29**: Never claim system-level Sortino from component tests (happened: ad-hoc script testing 2 modules claimed system-level results)
- **Rule 30**: Apply adversarial review before declaring dead-ends (happened: VRULE-017 prematurely rejected CEM, wasting weeks when overturned)
- **Rule 31**: Factorial interaction testing before combining findings (happened: 6 accepted findings combined produced WORSE results than baseline)
- **Rule 37**: Canonical fee model only (happened: three different fee rates in three scripts, all wrong)
- **Rule 38**: Dead signal detection before wiring (happened: funding signal had 0/73 hit rate, discovered months later)

**Rules 39-43 (Meta-findings):** Encode the strongest research conclusions directly into the development process:
- **Rule 39**: Always decompose aggregate signals into per-asset signals (+123% Sortino improvement)
- **Rule 42**: Per-asset funding rates are different (PAXG negative = income, original model was 16x overstated)

**Rules 44-53 (Deep audit):** Added after a 15-agent parallel audit found 53 bugs:
- **Rule 44**: Interface contract verification (wrong attribute names made recalibrator dead for entire session)
- **Rule 45**: No silent `except Exception: pass` (4 bugs hidden by bare except handlers)
- **Rule 46**: `default_factory` must be pure (network calls in dataclass defaults broke CI)
- **Rule 50**: Dead code audit per PR (19 dead modules accumulated over weeks)
- **Rule 52**: State persistence round-trip tests (positions wiped, equity reset, PnL lost — all from save/load asymmetry)

**Rules 54-62 (Live deployment + data plane):** Added after deploying to mainnet with real capital:
- **Rules 54-57**: Deployment verification and incident review — mandatory pre/post-deploy checklists, incident post-mortems with rule additions
- **Rules 58-62**: Data plane verification — production data must match expected schema, stale data detection, reconciliation between exchange state and internal state

### Why This Matters for Engineering Leaders

The rule set is a living document of **organizational learning encoded as automated constraints**. In a human team, this knowledge lives in tribal memory and code review judgment. In an AI-augmented system, it must be explicit — every lesson learned becomes a rule that applies to every future session, regardless of which agent picks up the work.

The progression from 10 to 62 rules also demonstrates the system's ability to learn from its own failures. Each rule has a documented incident that motivated it, making the contract simultaneously a policy document and a post-mortem archive.

---

## Dead Code Archival: 36,658 LOC Removed

One of the most significant engineering health milestones: a single PR archived 36,658 lines of dead code — dead modules, stale allocators, superseded orchestrators, and tests that only tested dead code.

The test count dropped by ~900 — but every removed test was testing dead code. This is healthy: the codebase got leaner without losing any coverage of living code. The metrics honestly reflect the change rather than preserving inflated numbers.

This archival was prompted by a red-team audit that identified architecture drift — documentation and code diverging over months of rapid development. The red-team audit also caught that governor sleeve_multipliers were computed but never propagated to the sizing pipeline (a no-op bug).

---

## Deep Audit: 15-Agent Parallel Bug Hunt

The most ambitious multi-agent operation was a 15-agent deep audit that found **53 bugs** across the full codebase. Each agent was assigned a specific audit scope:

| Agent | Scope | Bugs Found |
|-------|-------|------------|
| Signal integrity | L1 signal engines | 5 (sleeves never fired, EMA config dead code) |
| Execution layer | SOR + routing | 4 (health monitor thread safety, gate miscalculation) |
| State persistence | Save/load cycle | 3 (positions wiped, equity reset, PnL lost) |
| Interface contracts | Cross-component wiring | 6 (wrong attribute names, missing propagation) |
| Exception handling | Silent failures | 8 (bare except:pass hiding AttributeError, ImportError) |
| Dead code | Unused modules/methods | 19 modules identified |
| Data integrity | DB access patterns | 4 (missing busy_timeout, no LIMIT clauses) |
| Configuration | Default values | 3 (network calls in default_factory) |
| Others | Various | 1 remaining |

**12 PRs were merged in a single session**, each fixing a category of bugs. This audit also produced rules 44-53.

---

## Development Model: Continuous, Not Sprint-Based

The initial development used wave-based sprints (Wave 0 foundation → Wave 1 core → Wave 2 strategies → Wave 3 integration). This was effective for bootstrapping but insufficient for ongoing development where research findings continuously reshape the architecture.

The current model is **continuous parallel sessions**:

1. **Research sessions**: Test hypotheses, run factorial campaigns, generate findings
2. **Implementation sessions**: Wire accepted findings into production code
3. **Audit sessions**: Deep-scan for bugs, dead code, interface mismatches
4. **Infrastructure sessions**: Data pipeline expansion, daemon management, deployment
5. **Production sessions**: Live system monitoring, incident response, recalibration

Each session type has different agent configurations, verification requirements, and merge protocols. Research sessions are exploratory (more tolerance for throwaway code). Implementation sessions are strict (full verification, interface contract tests). Audit sessions are adversarial (explicitly trying to break things). Production sessions are safety-critical (deployment checklists, rollback plans).

---

## Lessons Learned

### What Works

1. **Git worktree isolation eliminates most file conflicts.** The conflict preflight catches the rest.
2. **Rules that encode failure modes prevent repeat incidents.** The 62-rule contract is proof.
3. **Interface contract tests catch the #1 bug category.** Silent integration failures from attribute name mismatches.
4. **Adversarial audit sessions find what normal development misses.** 53 bugs in one session.
5. **Canonical fee model prevents inconsistency.** Three different fee rates was the anti-pattern.
6. **Session-typed development prevents mode mixing.** Research sessions vs. implementation sessions have different quality bars.

### What Failed and Was Fixed

1. **Sprint model doesn't scale past initial build.** Replaced with continuous parallel sessions.
2. **"13 agents in one sprint" created coordination overhead.** Smaller, focused sessions are more effective.
3. **Silent exception handling hid critical bugs for weeks.** Now banned via Rule 45.
4. **Dead code accumulated without active cleanup.** Now audited per PR via Rule 50. A single archival PR removed 36,658 LOC.
5. **Aggregate signals masked per-asset opportunities.** Per-asset decomposition is now Rule 39.
6. **Live deployment revealed new failure categories.** State reconciliation, data plane verification, and margin accounting bugs only appeared under real trading conditions — prompting rules 54-62.

### Key Insight

The most valuable output of AI-augmented development is not the code — it is the **encoded institutional knowledge** in the agent contract, VRULE registry, and hypothesis database. These artifacts ensure that every future development session starts with the full context of what has been tried, what failed, and why. In a traditional team, this knowledge lives in people's heads and is lost to turnover. In VALEN, it is versioned, searchable, and automatically applied.

# AI Fleet Operation

## Overview

VALEN was built by a solo product/engineering leader operating a fleet of AI coding agents. The key output isn't the code — it's the **harness**: the 62-rule agent contract, the conflict preflight system, the merge orchestrator, and the verification gates that let multiple agents work in parallel without stepping on each other.

The result: **1,032 PRs, 5,301 tests, ~150K LOC, 127 hypotheses tested** — a production trading system designed, shipped, and live-hardened in ~4 weeks.

This document is about the agentic coding harness itself — the part that generalizes beyond VALEN. If you're evaluating signal on how I operate AI at scale, the harness matters more than any single PR.

---

## Scale

| Metric | Early (Month 1) | Current |
|--------|-----------------|---------|
| PRs merged | 18 | **1,032** |
| Tests | 497 | **5,301** across 401 files |
| Agent contract rules | 10 | **62** |
| Data daemons | 0 | **28** |
| Research hypotheses | 0 | **127** |
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

The agent contract is the most important artifact I built. It started with 10 basic rules and grew to 62 through a feedback loop: every production incident or research failure spawns a new rule that prevents recurrence. This is my engineering judgment, encoded as automated constraints.

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

### Why This Matters

In a human team, engineering judgment lives in tribal memory and code review intuition. When I operate AI agents, that judgment must be explicit and mechanical. The 62-rule contract is essentially a compressed engineering culture — every lesson from every failure, applied automatically to every future session.

This is the same problem engineering leaders face when scaling teams: how do you encode institutional knowledge so it survives turnover and applies consistently? The difference is that AI agents follow rules perfectly but have zero judgment about when rules conflict. **The "why" annotations on each rule let me (and the agents) make exceptions intelligently.** A rule without its incident history gets applied dogmatically; a rule with its incident history gets applied with judgment.

### Rule Quality Control

Not every rule that gets proposed becomes a rule. The acceptance bar has two conditions:

1. **The rule must prevent a specific, observed failure.** Speculative rules ("we should be careful about X") don't make it in. They get ignored; agents sense which rules are load-bearing and which are theater.
2. **The rule must have a clear enforcement mechanism.** Either CI grep-detection, test-file enforcement, pre-commit hook, or dedicated audit script. A rule that depends on human vigilance is a rule that will be forgotten.

VRULE-017 (CEM rejection, later overturned) is the cautionary tale. A rule that gets added without enough evidence, then has to be removed, damages the credibility of the entire rule system. Rule 40 now requires every VRULE to survive adversarial review on four dimensions (right data, right assets, right fee model, right signals) before becoming canonical. The meta-rule: **premature rules waste more time than premature absence.**

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

The most valuable output isn't the code — it's the **encoded institutional knowledge**: the agent contract, the VRULE registry, the hypothesis database. These ensure every future session starts with full context of what was tried, what failed, and why. In a traditional team, this knowledge lives in people's heads and is lost to turnover. In an AI-operated system, it's versioned, searchable, and automatically applied.

This is why I frame my role as fleet operator and harness builder, not coder. The agents write Python. I design the system that makes their Python correct.

---

## Post-Mainnet Audit Pattern: The Three-Way Verification

Once VALEN went live, a new class of audit emerged — not "does this code work" but "does the code, the deployed binary, and the data plane agree with each other?" Three independent facts that must reconcile before anything is "done":

1. **Code exists locally.** The file is in the git repo.
2. **Code is deployed.** The file is at `/opt/valen/src/...` on the EC2 host.
3. **The data plane supports it.** The DB, daemon, or feed it depends on is actually running with the expected schema.

An S4 module with tests passing locally is not "done" until all three are verified. Rule 58 (three-proof requirement) formalizes this. A single agent claiming "feature X works" is a local-fact agent; the deployment agent and the data-plane agent must independently confirm before the merge is considered complete.

This triggered a new session type: **reconciliation sessions.** An agent whose only job is to answer the question "does state A match state B?" for a specific pair of facts. The vol-drift staleness bug, the 17x equity lie, the invisible builder perps — all were caught or cleanly diagnosed by reconciliation sessions.

---

## Adversarial Audit Cadence

Adversarial audits (15-agent deep scans) are not one-time events. They run on a schedule:

| Cadence | Focus | Typical findings |
|---------|-------|------------------|
| Weekly | New-code audit (PRs merged that week) | Interface contracts, silent exceptions, dead paths |
| Monthly | Architecture drift audit | Components diverging from spec, stale docs, authority conflicts |
| Per-incident | Targeted audit on failure class | The vol-drift bug triggered a state-staleness audit across all state-bearing components |
| Pre-release | Full-system audit before major deploys | Comprehensive scan of the full component graph |

Each cadence has its own scope, agent count, and merge protocol. The weekly audit is light-touch (3-5 agents); the monthly is heavier (10-15); the pre-release is comprehensive (the original 15-agent format).

Audits produce two artifacts: **fix PRs** and **rule additions**. A finding that only produces a fix is weaker than one that also produces a rule — the fix is local, the rule prevents recurrence across all future sessions.

---

## The Authority Map: Agents and Composability

As the system matured, a subtle failure class emerged: two independently-correct components producing globally-incoherent behavior. The S4TargetPipeline and the TailRiskOverlay were each correct in isolation, but when S4 silently overrode the tail-mult reduction with no log, the system's apparent caution (visible in logs) didn't match its actual behavior (visible in orders).

I formalized an **authority map** — every sizing/policy component registered with explicit precedence rules against every other such component. 11 documented pairs. For each: who wins, under what conditions, how it's logged, what test verifies the rule.

New components can't merge without registering their authority relationships. This is the agentic-harness version of the problem every engineering leader eventually hits: two subsystems built by different teams that are each internally correct and jointly broken. The solution isn't "better code reviews"; it's a mechanical registry of composition rules.

---

## The Meta-Pattern

Every one of these harness features — git worktrees, conflict preflight, merge orchestrator, session typing, three-way verification, adversarial audits, authority map — shares a structure:

1. **A specific failure class was observed.**
2. **Instead of fixing the instance, the fix targeted the process.**
3. **The process fix is mechanical, not documented.** CI enforces it. Pre-commit hooks enforce it. Tests enforce it.
4. **The rule carries its incident history so agents can reason about edge cases.**

This is the engineering leadership pattern that scales, whether your "team" is 15 agents or 15 humans. Documentation describes what should happen. Mechanical enforcement makes it happen. The difference between a rule that prevents recurrence and a rule that gets ignored is whether it's grep-enforced, test-enforced, or merely aspirational.

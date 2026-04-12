#!/usr/bin/env bash
# VALEN Conflict Preflight Check
# Run at session start BEFORE picking up work to detect file-level conflicts
# with other active agents/PRs.
#
# Usage:
#   bash scripts/conflict_preflight.sh                  # check all open PRs
#   bash scripts/conflict_preflight.sh --files src/a.py src/b.py  # check specific files
#   bash scripts/conflict_preflight.sh --scope p1       # check pillar scope
#
# Exit codes:
#   0 — no conflicts detected, safe to proceed
#   1 — file overlap detected with active PRs (review before proceeding)
#   2 — exclusive zone contention (STOP — do not proceed without resolution)
set -uo pipefail

VALEN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$VALEN_ROOT"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Parse args ───────────────────────────────────────────────────────────────
CHECK_FILES=()
CHECK_SCOPE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --files) shift; while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do CHECK_FILES+=("$1"); shift; done ;;
        --scope) CHECK_SCOPE="$2"; shift 2 ;;
        *) shift ;;
    esac
done

echo -e "${CYAN}=== VALEN Conflict Preflight ===${NC}"
echo "Root: $VALEN_ROOT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# ── Exclusive zones (programmatic enforcement) ───────────────────────────────
EXCLUSIVE_ZONES=(
    "src/services/router/"
    "config/"
    "research/data/hypothesis_registry.json"
)

CHECK_FILES_JSON=$(printf '%s\n' "${CHECK_FILES[@]-}" | python3 -c 'import json,sys; print(json.dumps([line.strip() for line in sys.stdin if line.strip()]))')
EXCLUSIVE_ZONES_JSON=$(printf '%s\n' "${EXCLUSIVE_ZONES[@]}" | python3 -c 'import json,sys; print(json.dumps([line.strip() for line in sys.stdin if line.strip()]))')

python3 - "$VALEN_ROOT" "$CHECK_SCOPE" "$CHECK_FILES_JSON" "$EXCLUSIVE_ZONES_JSON" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys

root = sys.argv[1]
check_scope = sys.argv[2]
check_files = json.loads(sys.argv[3])
exclusive_zones = json.loads(sys.argv[4])

RED = "\033[0;31m"
YELLOW = "\033[1;33m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None


exit_code = 0
file_to_prs: dict[str, list[int]] = {}
pr_info: dict[int, str] = {}

print(f"{CYAN}--- [1/4] Scanning open PRs for file ownership ---{NC}")
pr_list = run(
    [
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--json",
        "number,headRefName,author,title",
        "--limit",
        "50",
    ]
)
open_prs: list[dict] = []
if pr_list is not None and pr_list.returncode == 0 and pr_list.stdout.strip():
    try:
        open_prs = json.loads(pr_list.stdout)
    except json.JSONDecodeError:
        open_prs = []

if not open_prs:
    print("  No open PRs found (or gh not available). Skipping PR conflict check.")
else:
    print(f"  Found {len(open_prs)} open PR(s). Scanning changed files...")
    for pr in open_prs:
        pr_num = int(pr["number"])
        pr_info[pr_num] = f'{pr["headRefName"]}|{pr["title"][:60]}'
        diff = run(["gh", "pr", "diff", str(pr_num), "--name-only"])
        if diff is None or diff.returncode != 0:
            continue
        for file in (line.strip() for line in diff.stdout.splitlines()):
            if not file:
                continue
            file_to_prs.setdefault(file, [])
            if pr_num not in file_to_prs[file]:
                file_to_prs[file].append(pr_num)
    print(f"  Indexed {len(file_to_prs)} files across {len(open_prs)} PRs.")
print()

print(f"{CYAN}--- [2/4] Detecting inter-PR file overlaps ---{NC}")
overlaps = {file: prs for file, prs in file_to_prs.items() if len(prs) > 1}
if not overlaps:
    print(f"  {GREEN}No inter-PR file overlaps detected.{NC}")
else:
    for file, prs in sorted(overlaps.items()):
        joined = ",".join(str(pr) for pr in prs)
        print(f"  {YELLOW}OVERLAP: {file} → PRs: {joined}{NC}")
    print()
    print(f"  {YELLOW}{len(overlaps)} file(s) touched by multiple PRs.{NC}")
    print("  These PRs must be merged in dependency order (see merge_orchestrator.sh).")
    exit_code = max(exit_code, 1)
print()

print(f"{CYAN}--- [3/4] Checking exclusive zone contention ---{NC}")
exclusive_violations = 0
for zone in exclusive_zones:
    zone_prs = sorted(
        {
            pr
            for file, prs in file_to_prs.items()
            if file.startswith(zone)
            for pr in prs
        }
    )
    if len(zone_prs) > 1:
        exclusive_violations += 1
        print(f"  {RED}EXCLUSIVE ZONE VIOLATION: {zone}{NC}")
        print(
            f"  {RED}  Contested by PRs: {' '.join(str(pr) for pr in zone_prs)}{NC}"
        )
        for pr in zone_prs:
            print(f"    PR #{pr}: {pr_info.get(pr, 'unknown')}")
        exit_code = 2
    elif len(zone_prs) == 1:
        print(f"  {GREEN}{zone} — owned by PR #{zone_prs[0]}{NC}")
    else:
        print(f"  {GREEN}{zone} — uncontested{NC}")

if exclusive_violations:
    print()
    print(f"  {RED}{exclusive_violations} exclusive zone violation(s)!{NC}")
    print(f"  {RED}STOP: Resolve ownership before proceeding.{NC}")
print()

if check_files:
    print(f"{CYAN}--- [4/4] Checking your planned files against active PRs ---{NC}")
    conflicts = 0
    for file in check_files:
        prs = file_to_prs.get(file)
        if prs:
            conflicts += 1
            joined = ",".join(str(pr) for pr in prs)
            print(f"  {YELLOW}CONFLICT: {file} is owned by PR(s): {joined}{NC}")
    if conflicts == 0:
        print(f"  {GREEN}All {len(check_files)} planned files are clear.{NC}")
    else:
        print(f"  {YELLOW}{conflicts} of {len(check_files)} files have active owners.{NC}")
        exit_code = max(exit_code, 1)
elif check_scope:
    print(f"{CYAN}--- [4/4] Checking scope '{check_scope}' against active PRs ---{NC}")
    scope_conflicts = 0
    for file, prs in sorted(file_to_prs.items()):
        if check_scope in file:
            scope_conflicts += 1
            joined = ",".join(str(pr) for pr in prs)
            print(f"  {YELLOW}SCOPE OVERLAP: {file} → PRs: {joined}{NC}")
    if scope_conflicts == 0:
        print(f"  {GREEN}No active PRs touch scope '{check_scope}'.{NC}")
else:
    print("--- [4/4] No specific files/scope to check (pass --files or --scope) ---")
print()

print(f"{CYAN}--- [BONUS] Active worktree summary ---{NC}")
worktrees = run(["git", "worktree", "list"])
worktree_lines = (
    [line for line in worktrees.stdout.splitlines() if line.strip()]
    if worktrees is not None and worktrees.returncode == 0
    else []
)
merged = run(["git", "branch", "--merged", "main"])
merged_branches = {
    line.replace("*", "").strip()
    for line in (merged.stdout.splitlines() if merged is not None else [])
    if line.strip()
}
stale = 0
for line in worktree_lines[1:]:
    if "[" not in line or "]" not in line:
        continue
    branch = line.split("[", 1)[1].split("]", 1)[0]
    if branch in merged_branches:
        stale += 1
print(f"  Active worktrees: {len(worktree_lines)}")
print(f"  Potentially stale (merged to main): {stale}")
if stale > 3:
    print(f"  {YELLOW}Consider running: bash scripts/worktree_cleanup.sh{NC}")
print()

print("========================================")
if exit_code == 0:
    print(f"{GREEN}=== Preflight CLEAR — no conflicts detected ==={NC}")
elif exit_code == 1:
    print(
        f"{YELLOW}=== Preflight WARNING — file overlaps detected (review before proceeding) ==={NC}"
    )
else:
    print(
        f"{RED}=== Preflight BLOCKED — exclusive zone contention (resolve first) ==={NC}"
    )

sys.exit(exit_code)
PY
exit $?

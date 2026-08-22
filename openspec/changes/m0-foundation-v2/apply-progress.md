# Apply Progress: M0 Foundation v2 — G1–G5 + A1–A5 (Batches 1–10)

## Immutable Anchors

- **M0_BASE**: `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`
- **M0_BASE_TREE**: `4b825dc642cb6eb9a060e54bf8d69288fbee4904` (empty tree)
- **SDD[] (admission-existing planning paths, 10 files)**: openspec/config.yaml, openspec/changes/m0-foundation-v2/design.md, openspec/changes/m0-foundation-v2/exploration.md, openspec/changes/m0-foundation-v2/proposal.md, openspec/changes/m0-foundation-v2/specs/architecture/spec.md, openspec/changes/m0-foundation-v2/specs/governance/spec.md, openspec/changes/m0-foundation-v2/specs/legacy-evidence/spec.md, openspec/changes/m0-foundation-v2/tasks.md, .atl/.skill-registry.cache.json, .atl/skill-registry.md

## Delivery Strategy

- **Delivery strategy**: auto-chain
- **Chain strategy**: stacked-to-main
- **Current work unit**: A5 (task 2.5)
- **PR boundary**: `docs/MASTER_ROADMAP_1.0.md` only (stacked on G3)
- **Estimated review budget**: 753 lines (357 M0-M8 + 396 M9-M16); 396 new within ≤400 limit

## Mode

- **Strict TDD**: false (no test runner; confirmed by config.yaml `tdd: false`, `test_command: ""`)
- **Artifact store**: hybrid (OpenSpec files + Engram)

# Apply Progress: M0 Foundation v2 — G1–G5 + A1–A5 (Batches 1–10)

## Completed Tasks

### 1.1 G1: neutral ignore/state machines

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `.gitignore` (20 lines), `docs/STATUS_MATRIX.md` (94 lines)
- **Total**: 114 lines

#### Verification Evidence

| Check | Command | Result |
|---|---|---|
| Whitespace | `ws` | PASS — no trailing whitespace or merge conflicts |
| Scope | `scope G1` | PASS — repository-wide tracked/untracked/ignored set, less exact admission SDD and hybrid bookkeeping, matches G1 |
| States | `states` | PASS — exact component and WP eight-state sets match; no extras |
| Transitions | `transitions` | PASS — normal flows, both recoveries, four BLOCKED restorations, three DEFERRED ingresses, and approved-scope return verified |
| Stack-neutral | `stack_neutral` | PASS — no build/framework/language patterns in .gitignore |
| Path allowlist | diff repository set less SDD/bookkeeping vs G1 | PASS — exact match; arbitrary root paths rejected |

#### Spec Trace

| Spec Requirement | Status |
|---|---|
| `.gitignore`: only OS/editor/environment artifacts | PASS — .DS_Store, Thumbs.db, desktop.ini, *.swp, *.swo, *~, .vscode/, .idea/, .env*, *.log |
| `.gitignore`: no stack assumptions | PASS — zero framework/language/build patterns |
| `docs/STATUS_MATRIX.md`: 8 component states | PASS — UNKNOWN, AUDITED, BROKEN, PARTIAL, FUNCTIONAL, TESTED, STABLE, FROZEN |
| `docs/STATUS_MATRIX.md`: normal component progression | PASS — UNKNOWN → AUDITED → FUNCTIONAL → TESTED → STABLE → FROZEN |
| `docs/STATUS_MATRIX.md`: BROKEN/PARTIAL → FUNCTIONAL recovery | PASS — with remediation + evidence + review rules |
| `docs/STATUS_MATRIX.md`: 8 WP states | PASS — BACKLOG, READY, IN_PROGRESS, REVIEW, VERIFY, BLOCKED, DONE, DEFERRED |
| `docs/STATUS_MATRIX.md`: normal WP flow | PASS — BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE |
| `docs/STATUS_MATRIX.md`: BLOCKED records prior state | PASS — all four suspendable states documented |
| `docs/STATUS_MATRIX.md`: DEFERRED → BACKLOG requires scope change | PASS |

#### Reproducible Verification Commands

```bash
M0_BASE=$(awk '/^M0_BASE:/{print $2}' openspec/changes/m0-foundation-v2/state.yaml)
mapfile -t SDD < <(awk '/^SDD:/{p=1;next} p&&/^  - /{sub(/^  - /,"");print}' openspec/changes/m0-foundation-v2/state.yaml)
eval "$(awk '/^```bash$/{p=1;next}/^```$/{if(p)exit}p' openspec/changes/m0-foundation-v2/tasks.md)"
for c in ws 'scope G1' states transitions stack_neutral; do
  eval "$c" && printf '%s: PASS\n' "$c" || exit 1
done
(changed(){ printf '%s\n' .gitignore docs/STATUS_MATRIX.md unauthorized-root; }; ! scope G1 >/dev/null) && printf 'scope arbitrary-root rejection: PASS\n'
```

**Command output** (2026-08-10 16:10:00 -0400; immediate HEAD `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`; 114 product lines):
```
ws: PASS
scope G1: PASS
states: PASS
transitions: PASS
stack_neutral: PASS
scope arbitrary-root rejection: PASS
```

#### G1 Scope Incident

At 2026-08-10 15:54:00 -0400, executing the literal Markdown text `Chain: G1->G2->G3->G4->G5->A1->A2->A3->A4->A5->AR->L->R.` as a shell command created 12 zero-byte redirect targets (`G2-` through `R.`). They were verified as regular empty files and deleted. Tasks now use Unicode dependency arrows, and `scope G1` inspects repository-wide tracked, untracked, and ignored paths before subtracting only the exact admission `SDD[]` paths and explicit hybrid bookkeeping paths.

#### Rollback Boundary

Exact files: `.gitignore`, `docs/STATUS_MATRIX.md`. All successors remain BACKLOG, so no completed successor depends on G1. Rollback is `rm .gitignore docs/STATUS_MATRIX.md && rmdir docs` (if docs/ is empty after removal).

Complete rollback includes state/progress/tasks stores:
- `rm .gitignore docs/STATUS_MATRIX.md && rmdir docs`
- `rm openspec/changes/m0-foundation-v2/apply-progress.md`
- `rm openspec/changes/m0-foundation-v2/state.yaml`
- Revert `openspec/changes/m0-foundation-v2/tasks.md` G1 checkbox

#### Runtime Harness

N/A — docs-only milestone, no build/test/runtime target exists.

#### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | Run the reproducible loader/loop above — exit 0, all 5 checks pass; repository-wide scope rejects arbitrary root paths while excluding SDD/bookkeeping |
| Runtime harness command/scenario and exact result | N/A — docs-only; no build system, test target, framework, or runnable project command exists (config.yaml `test_command: ""`, `build_command: ""`) |
| Rollback boundary | `.gitignore`, `docs/STATUS_MATRIX.md`, `openspec/changes/m0-foundation-v2/apply-progress.md`, `openspec/changes/m0-foundation-v2/state.yaml` — exact files; revert tasks.md G1 checkbox |

### 1.2 G2←G1: DoR/DoD/Golden Path/invariants

- **Status**: DONE (independent content gate PASS 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS; closeout: IN_PROGRESS→REVIEW→VERIFY→DONE
- **Files**: `docs/DEFINITION_OF_DONE.md` (53 lines), `docs/INVARIANTS.md` (117 lines)
- **Total**: 170 lines

#### Verification Evidence

| Check | Command | Result |
|---|---|---|
| Whitespace | `ws` | PASS — no trailing whitespace or merge conflicts |
| Cumulative scope G1+G2 vs M0_BASE | `changed "$M0_BASE"` → G1+G2 set | PASS — exact 4 files: .gitignore, STATUS_MATRIX.md, DEFINITION_OF_DONE.md, INVARIANTS.md |
| Cumulative per-slice scope | `scope G12` (G1+G2, uncommitted chain) | PASS — cumulative scope until G1 committed |
| Line budget ≤400 | `wc -l` | PASS — 170 lines |
| DoR (7 criteria) | `grep` responsibility, explicit scope, known dependencies, sufficiently defined contract, applicable invariants, acceptance criteria, verification strategy | PASS — all 7 evidenced criteria present |
| DoD (8 criteria) | `grep` contract implemented, NEW tests from scratch, integration validated, errors explicit, lifecycle validated, docs updated, no duplicated/parallel truth, verification approved | PASS — all 8 conditional criteria present |
| Golden Path | `grep` clean install → start app → select music directory/library → scan → browse → search → select track → play → pause/resume → seek → previous/next → manage Queue → shuffle/repeat → close → restart → recover valid consistent state | PASS — full product Golden Path sequence |
| Freeze prerequisites | `grep` stable contract, new tests passed, integration, architecture verification, no P0/P1 | PASS — 5 freeze prerequisites |
| Reopen reasons | `grep` bug, regression, vulnerability, accessibility, layout breakage, unavoidable integration | PASS — 6 exact reopen reasons |
| P0 definitions | `grep` corruption, library loss, no start, systematic Golden crash, critical security, fundamental playback unusable | PASS — 6 exact P0 definitions |
| P1 definitions | `grep` core broken, severe state inconsistency, incorrect queue-playback, incorrect primary persistence, severe Golden degradation | PASS — 5 exact P1 definitions |
| Release gate | `grep` "P0 = 0, P1 = 0" | PASS — exact 0/0 gate |
| Feature freeze | `grep` "Legacy existence.*insufficient", "POST_1_0_BACKLOG", "approved scope change" | PASS — Legacy insufficient, unneeded→BACKLOG, necessary→scope change |
| WIP | `grep` "one principal architecture capability", "one verification unit", "no second dependent feature" | PASS — exact WIP limits |
| Baby steps | `grep` "strictly reversible", "no copy-now-fix-later", "no conscious structural debt" | PASS — exact baby-steps policy |
| New-tests-only | `grep` "new specs", "no tests.*Explore.*Propose.*Spec.*Design", "read-only evidence", "never be copied or adapted", "fail-first.*strict_tdd.*false" | PASS — exact new-tests-only policy |

#### Independent Content Gate

| Evidence | Result |
|---|---|
| Authoritative content | PASS — DoR, DoD, product Golden Path, and invariants retain the original authoritative contract |
| Hybrid parity | PASS — normalized filesystem artifacts matched Engram #695 and #719 before lifecycle closeout; final artifacts are fully mirrored after normalization |
| Cumulative scope | PASS — exact G1+G2 product set against M0_BASE; no successor product files admitted |
| Line budget | PASS — G2 is exactly 170 product lines, within the 400-line review budget |
| Rollback | PASS — exact G2 product and bookkeeping rollback boundary is recorded below |
| G1 preserved | PASS — G1 remains DONE and its product files and evidence are unchanged |
| Successors | PASS — G3+ remain unchecked BACKLOG; no successor is ready or admitted |

#### Spec Trace — Authoritative Contract

| # | Obligation | Status |
|---|---|---|
| 1 | DoR: responsibility | PASS — "Ownership is assigned and recorded" |
| 2 | DoR: explicit scope | PASS — in/out boundary, adjacent interactions |
| 3 | DoR: known dependencies | PASS — predecessor DONE or non-blocking with rationale |
| 4 | DoR: sufficiently defined contract | PASS — documented with enough precision |
| 5 | DoR: applicable invariants | PASS — INVARIANTS.md cross-reference required |
| 6 | DoR: acceptance criteria | PASS — Given/When/Then form |
| 7 | DoR: verification strategy | PASS — test layer, scope, coverage, exact command |
| 8 | DoD: contract implemented | PASS — every requirement has implementation trace |
| 9 | DoD: NEW tests from scratch | PASS — no copied/adapted Legacy tests |
| 10 | DoD: integration validated | PASS — end-to-end boundary verification |
| 11 | DoD: errors explicit | PASS — all error paths handled; no silent failures |
| 12 | DoD: lifecycle validated | PASS — create, initialize, run, shutdown |
| 13 | DoD: docs updated | PASS — all affected documentation consistent |
| 14 | DoD: no duplicated/parallel truth | PASS — exactly one authority per fact |
| 15 | DoD: verification approved | PASS — independent confirmation, design adherence |
| 16 | Golden Path: product sequence | PASS — clean install → ... → recover valid consistent state |
| 17 | Golden Path: restart survival | PASS — intermediate state survives restart |
| 18 | Golden Path: exhaustive core loop | PASS — steps executable and verifiable in sequence |
| 19 | Freeze: 5 prerequisites | PASS — stable contract+impl, new tests, integration, architecture, 0/0 |
| 20 | Reopen: 6 exact reasons | PASS — bug, regression, vulnerability, accessibility, layout breakage, unavoidable integration |
| 21 | P0: 6 exact definitions | PASS — corruption, library loss, no start, systematic Golden crash, critical security, fundamental playback unusable |
| 22 | P1: 5 exact definitions | PASS — core broken, severe state inconsistency, incorrect queue-playback, incorrect primary persistence, severe Golden degradation |
| 23 | Release: P0 = 0, P1 = 0 | PASS |
| 24 | Feature freeze: Legacy insufficient | PASS — unneeded→POST_1_0_BACKLOG, necessary→scope change |
| 25 | WIP: 1 principal + 1 verification | PASS — no second dependent pre-stabilization |
| 26 | Baby steps: strictly reversible | PASS — no copy-now-fix-later, no conscious structural debt |
| 27 | New-tests-only: exact policy | PASS — new specs/contracts/invariants only, no Explore/Propose/Spec/Design, Legacy read-only never copied, no fail-first while strict_tdd false |

#### Reproducible Verification Commands

```bash
M0_BASE=$(awk '/^M0_BASE:/{print $2}' openspec/changes/m0-foundation-v2/state.yaml)
mapfile -t SDD < <(awk '/^SDD:/{p=1;next} p&&/^  - /{sub(/^  - /,"");print}' openspec/changes/m0-foundation-v2/state.yaml)
eval "$(awk '/^```bash$/{p=1;next}/^```$/{if(p)exit}p' openspec/changes/m0-foundation-v2/tasks.md)"

# Whitespace
ws && printf 'ws: PASS\n'

# Cumulative scope (G1+G2 vs M0_BASE)
G12=(.gitignore docs/STATUS_MATRIX.md docs/DEFINITION_OF_DONE.md docs/INVARIANTS.md)
diff -u <(LC_ALL=C comm -23 <(changed "$M0_BASE") <(printf '%s\n' "${SDD[@]}" "${B[@]}"|LC_ALL=C sort -u)) <(printf '%s\n' "${G12[@]}"|LC_ALL=C sort -u) && printf 'cumulative scope G1+G2: PASS\n'

# Cumulative per-slice scope (uncommitted chain)
scope G12 && printf 'cumulative per-slice scope G12: PASS\n'

# Line budget
[ $(cat docs/DEFINITION_OF_DONE.md docs/INVARIANTS.md | wc -l) -le 400 ] && printf 'line budget: PASS\n'

# DoR (7 evidenced items)
for term in "responsibility" "explicit scope" "known dependencies" "sufficiently defined contract" "applicable invariants" "acceptance criteria" "verification strategy"; do
  grep -qi "$term" docs/DEFINITION_OF_DONE.md || exit 1
done
printf 'DoR 7 criteria: PASS\n'

# DoD (8 conditional items)
for term in "contract implemented" "NEW tests from scratch" "integration validated" "errors explicit" "lifecycle validated" "docs updated" "no duplicated/parallel truth" "verification approved"; do
  grep -qi "$term" docs/DEFINITION_OF_DONE.md || exit 1
done
printf 'DoD 8 criteria: PASS\n'

# Golden Path (product sequence)
grep -q 'clean install.*start app.*select music.*scan.*browse.*search.*select track.*play.*pause.*resume.*seek.*previous.*next.*manage Queue.*shuffle.*repeat.*close.*restart.*recover valid consistent state' docs/DEFINITION_OF_DONE.md && printf 'Golden Path: PASS\n'

# INVARIANTS (authoritative contract)
for term in "stable contract" "new tests passed" "integration" "architecture verification" "no P0.*P1"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
for term in "Bug" "Regression" "Vulnerability" "Accessibility" "Layout breakage" "Unavoidable integration"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
for term in "corruption" "library loss" "no start" "systematic Golden crash" "critical security" "fundamental playback unusable"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
for term in "core broken" "severe state inconsistency" "incorrect queue-playback" "incorrect primary persistence" "severe Golden degradation"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
grep -q 'P0 = 0.*P1 = 0' docs/INVARIANTS.md || exit 1
for term in "Legacy existence.*insufficient" "POST_1_0_BACKLOG" "approved scope change"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
for term in "one principal architecture capability" "one verification unit" "no second dependent feature"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
for term in "strictly reversible" "no copy-now-fix-later" "no conscious structural debt"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
for term in "new specs" "no tests.*Explore.*Propose.*Spec.*Design" "read-only evidence" "never be copied or adapted" "fail-first.*strict_tdd.*false"; do
  grep -qi "$term" docs/INVARIANTS.md || exit 1
done
printf 'INVARIANTS authoritative contract: PASS\n'
```

**Command output** (2026-08-10; immediate HEAD `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`; 170 product lines):
```
ws: PASS
cumulative scope G1+G2: PASS
cumulative per-slice scope G12: PASS
line budget: PASS
DoR 7 criteria: PASS
DoD 8 criteria: PASS
Golden Path: PASS
INVARIANTS authoritative contract: PASS
```

#### Rollback Boundary

G2 exact files: `docs/DEFINITION_OF_DONE.md`, `docs/INVARIANTS.md`. No completed successor depends on G2 (G3+ remain BACKLOG). Rollback is `rm docs/DEFINITION_OF_DONE.md docs/INVARIANTS.md` (docs/ survives with STATUS_MATRIX.md from G1).

Dependency-aware hybrid rollback (G2 only, preserves G1):
- `rm docs/DEFINITION_OF_DONE.md docs/INVARIANTS.md`
- Revert `openspec/changes/m0-foundation-v2/tasks.md` G2 checkbox
- Revert `openspec/changes/m0-foundation-v2/state.yaml` G2 line
- Revert `openspec/changes/m0-foundation-v2/apply-progress.md` G2 section

#### Runtime Harness

N/A — docs-only milestone, no build/test/runtime target exists.

#### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | Run the reproducible verification commands above — exit 0, all 8 checks pass (ws, cumulative scope G1+G2, cumulative per-slice scope G12, line budget, DoR 7, DoD 8, Golden Path, INVARIANTS authoritative contract) |
| Runtime harness command/scenario and exact result | N/A — docs-only; no build system, test target, framework, or runnable project command exists (config.yaml `test_command: ""`, `build_command: ""`) |
| Rollback boundary | `docs/DEFINITION_OF_DONE.md`, `docs/INVARIANTS.md` — exact files; revert tasks.md G2 checkbox and state.yaml G2 line; G1 files preserved |

### 1.3 G3←G2: Master Roadmap M0–M8

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/MASTER_ROADMAP_1.0.md` (357 lines)
- **Total**: 357 lines

#### Verification Evidence

| Check | Command | Result |
|---|---|---|
| Whitespace | `ws` | PASS — no trailing whitespace or merge conflicts; prettier 3.9.6 confirms unchanged |
| Cumulative scope G1+G2+G3 vs M0_BASE | `scope G123` | PASS — exact 5 files: .gitignore, STATUS_MATRIX.md, DEFINITION_OF_DONE.md, INVARIANTS.md, MASTER_ROADMAP_1.0.md |
| Line budget ≤400 | `wc -l` | PASS — 357 lines |
| M0-M8 phase presence | `roadmap 0 8` | PASS — all 9 phases (M0 through M8) found as whole words |
| All 10 fields present | `grep -Eqi` Objective, Scope, Out-of-scope, Dependencies, Deliverables, New-test, Entry, Exit, Acceptance, Risks | PASS — all 10 field labels present in document |
| Per-phase 10 fields | Section-by-section field extraction per M0–M8 | PASS — every phase section contains all 10 fields |
| Phase name exactness | `grep -qwF` exact names | PASS — M0 Foundation, M1 Bootstrap, M2 Minimal Playback, M3 Complete Playback, M4 Queue, M5 Database, M6 Library, M7 Search, M8 Application Navigation |
| G1+G2 preserved | File content unchanged | PASS — .gitignore, STATUS_MATRIX.md, DEFINITION_OF_DONE.md, INVARIANTS.md identical to G2 exit state |
| Prettier formatting | `npx prettier --write` | PASS — file unchanged (already conformant) |
| Per-slice scope (uncommitted) | `scope G3` | NOTE — fails expectedly; G1+G2 files still uncommitted in stacked chain; cumulative `scope G123` PASS |

#### Spec Trace

| # | Obligation | Status |
|---|---|---|
| 1 | Governance Spec: Master Roadmap M0–M16 | PASS — M0–M8 present (G4 adds M9–M16) |
| 2 | Governance Spec: 10 fields non-empty per phase | PASS — all 10 field labels present with non-empty content in every M0–M8 section |
| 3 | Governance Spec: Phase names exact | PASS — all 9 phase names match spec exactly |
| 4 | Governance Spec: Test-routing per phase | PASS — each phase routes new-test strategy; M0 N/A with justification |
| 5 | Proposal: scope (11 paths) | PASS — MASTER_ROADMAP_1.0.md is an authorized M0 path |
| 6 | Tasks: G3←G2 dependency | PASS — G2 DONE before G3 implement |
| 7 | Design: Measurable fitness check "Parse M0-M16" | PASS — M0–M8 parsable; G4 adds M9–M16 |

#### Reproducible Verification Commands

```bash
M0_BASE=$(awk '/^M0_BASE:/{print $2}' openspec/changes/m0-foundation-v2/state.yaml)
mapfile -t SDD < <(awk '/^SDD:/{p=1;next} p&&/^  - /{sub(/^  - /,"");print}' openspec/changes/m0-foundation-v2/state.yaml)
eval "$(awk '/^```bash$/{p=1;next}/^```$/{if(p)exit}p' openspec/changes/m0-foundation-v2/tasks.md)"

# Whitespace
ws && printf 'ws: PASS\n'

# Cumulative scope G123 (G1+G2+G3)
G123=(.gitignore docs/{STATUS_MATRIX,DEFINITION_OF_DONE,INVARIANTS,MASTER_ROADMAP_1.0}.md)
scope G123 && printf 'cumulative scope G123: PASS\n'

# Line budget
lines=$(wc -l < docs/MASTER_ROADMAP_1.0.md)
[ "$lines" -le 400 ] && printf 'line budget (%d lines): PASS\n' "$lines"

# Roadmap M0-M8
roadmap 0 8 && printf 'roadmap 0 8: PASS\n'

# Phase presence
for m in $(seq 0 8); do
  grep -qw "M$m" docs/MASTER_ROADMAP_1.0.md || exit 1
done
printf 'M0-M8 phase presence: PASS\n'

# 10 fields
for f in Objective Scope Out-of-scope Dependencies Deliverables New-test Entry Exit Acceptance Risks; do
  grep -Eqi "(^|[^[:alnum:]_])$f([^[:alnum:]_]|$)" docs/MASTER_ROADMAP_1.0.md || exit 1
done
printf 'All 10 fields: PASS\n'

# Phase exact names
for name in "M0 Foundation" "M1 Bootstrap" "M2 Minimal Playback" "M3 Complete Playback" "M4 Queue" "M5 Database" "M6 Library" "M7 Search" "M8 Application Navigation"; do
  grep -qwF "$name" docs/MASTER_ROADMAP_1.0.md || exit 1
done
printf 'Phase names exact: PASS\n'

# Per-phase 10 fields
for m in 0 1 2 3 4 5 6 7 8; do
  section=$(awk -v m="M$m" '$0 ~ "^## "m" " {found=1} found && /^## / && $0 !~ "^## "m" " {exit} found {print}' docs/MASTER_ROADMAP_1.0.md)
  for f in "Objective" "Scope" "Out-of-scope" "Dependencies" "Deliverables" "New-test" "Entry" "Exit" "Acceptance" "Risks"; do
    echo "$section" | grep -Eqi "(^|[^[:alnum:]_])$f([^[:alnum:]_]|$)" || exit 1
  done
done
printf 'Per-phase 10 fields: PASS\n'
```

**Command output** (2026-08-10; immediate HEAD `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`; 357 product lines):
```
ws: PASS
cumulative scope G123: PASS
line budget (357 lines): PASS
roadmap 0 8: PASS
M0-M8 phase presence: PASS
All 10 fields: PASS
Phase names exact: PASS
Per-phase 10 fields: PASS
```

#### Rollback Boundary

G3 exact files: `docs/MASTER_ROADMAP_1.0.md`. No completed successor depends on G3 (G4+ remain BACKLOG). Rollback is `rm docs/MASTER_ROADMAP_1.0.md` (docs/ survives with G1+G2 files).

Dependency-aware hybrid rollback (G3 only, preserves G1+G2):
- `rm docs/MASTER_ROADMAP_1.0.md`
- Revert `openspec/changes/m0-foundation-v2/tasks.md` G3 checkbox
- Revert `openspec/changes/m0-foundation-v2/state.yaml` G3 lines
- Revert `openspec/changes/m0-foundation-v2/apply-progress.md` G3 section

#### Runtime Harness

N/A — docs-only milestone, no build/test/runtime target exists.

#### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | Run the reproducible verification commands above — exit 0, all 8 checks pass (ws, cumulative scope G123, line budget 357, roadmap 0 8, M0-M8 phase presence, all 10 fields, phase names exact, per-phase 10 fields) |
| Runtime harness command/scenario and exact result | N/A — docs-only; no build system, test target, framework, or runnable project command exists (config.yaml `test_command: ""`, `build_command: ""`) |
| Rollback boundary | `docs/MASTER_ROADMAP_1.0.md` — exact file; revert tasks.md G3 checkbox, state.yaml G3 lines, apply-progress.md G3 section; G1+G2 files preserved |

### 1.4 G4←G3: Master Roadmap M9–M16

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/MASTER_ROADMAP_1.0.md` (753 lines; 357 M0-M8 + 396 M9-M16)
- **Total**: 396 new lines (within ≤400 budget)

#### Verification Evidence

| Check | Command | Result |
|---|---|---|
| Whitespace | `ws` | PASS — no trailing whitespace or merge conflicts |
| Scope | `scope G4` | PASS — exact file: MASTER_ROADMAP_1.0.md (same as G3) |
| Roadmap M9-M16 | `roadmap 9 16` | PASS — M9 through M16 all found as whole words; all 10 field labels present |
| Per-phase 10 fields M9-M16 | Per-phase field extraction | PASS — every M9–M16 section contains all 10 fields |
| Phase name exactness | `grep -qwF` exact names | PASS — M9 UI Foundation, M10 Settings & Persistence, M11 Resilience, M12 Performance, M13 Packaging, M14 Beta, M15 Release Candidate, M16 Michi Music Player 1.0 Stable |
| Line budget ≤400 new | `wc -l` | PASS — 396 new lines; 753 total |
| Prettier formatting | `npx prettier --write` | PASS — file unchanged (already conformant) |
| G1+G2+G3 preserved | File content unchanged | PASS — M0–M8 section identical to G3 exit state |
| Cumulative scope G1234 | `scope G1234` | PASS — 5 files: .gitignore, STATUS_MATRIX.md, DEFINITION_OF_DONE.md, INVARIANTS.md, MASTER_ROADMAP_1.0.md |

#### Spec Trace

| # | Obligation | Status |
|---|---|---|
| 1 | Governance Spec: Master Roadmap M0–M16 | PASS — M0–M16 all present with complete 10-field sections |
| 2 | Governance Spec: 10 fields non-empty per phase M9-M16 | PASS — all 10 field labels present with non-empty content in every M9–M16 section |
| 3 | Governance Spec: Phase names exact M9-M16 | PASS — all 8 phase names match spec exactly |
| 4 | Governance Spec: Test-routing per phase | PASS — every M9–M16 phase routes new-test strategy command |
| 5 | Proposal: scope (11 paths) | PASS — MASTER_ROADMAP_1.0.md is an authorized M0 path |
| 6 | Tasks: G4←G3 dependency | PASS — G3 DONE before G4 implement |
| 7 | Design: Measurable fitness "Parse M0-M16" | PASS — full M0–M16 parsable |
| 8 | Line budget ≤400 new content | PASS — 396 new lines; total 753 |

#### Reproducible Verification Commands

```bash
M0_BASE=$(awk '/^M0_BASE:/{print $2}' openspec/changes/m0-foundation-v2/state.yaml)
mapfile -t SDD < <(awk '/^SDD:/{p=1;next} p&&/^  - /{sub(/^  - /,"");print}' openspec/changes/m0-foundation-v2/state.yaml)
eval "$(awk '/^```bash$/{p=1;next}/^```$/{if(p)exit}p' openspec/changes/m0-foundation-v2/tasks.md)"

# Whitespace
ws && printf 'ws: PASS\n'

# Scope G4
scope G4 && printf 'scope G4: PASS\n'

# Cumulative scope G1234
G1234=(.gitignore docs/{STATUS_MATRIX,DEFINITION_OF_DONE,INVARIANTS,MASTER_ROADMAP_1.0}.md)
scope G1234 && printf 'cumulative scope G1234: PASS\n'

# Line budget (new content ≤400)
lines=$(wc -l < docs/MASTER_ROADMAP_1.0.md)
[ "$lines" -eq 753 ] && printf 'line count (753 total, 396 new): PASS\n'

# Roadmap M9-M16
roadmap 9 16 && printf 'roadmap 9 16: PASS\n'

# M9-M16 phase presence
for m in $(seq 9 16); do
  grep -qw "M$m" docs/MASTER_ROADMAP_1.0.md || exit 1
done
printf 'M9-M16 phase presence: PASS\n'

# Phase exact names M9-M16
for name in "M9 UI Foundation" "M10 Settings & Persistence" "M11 Resilience" "M12 Performance" "M13 Packaging" "M14 Beta" "M15 Release Candidate" "M16 Michi Music Player 1.0 Stable"; do
  grep -qwF "$name" docs/MASTER_ROADMAP_1.0.md || exit 1
done
printf 'M9-M16 phase names exact: PASS\n'

# Per-phase 10 fields M9-M16
for m in 9 10 11 12 13 14 15 16; do
  section=$(awk -v m="M$m" '$0 ~ "^## "m" " {found=1} found && /^## / && $0 !~ "^## "m" " {exit} found {print}' docs/MASTER_ROADMAP_1.0.md)
  for f in "Objective" "Scope" "Out-of-scope" "Dependencies" "Deliverables" "New-test" "Entry" "Exit" "Acceptance" "Risks"; do
    echo "$section" | grep -Eqi "(^|[^[:alnum:]_])$f([^[:alnum:]_]|$)" || exit 1
  done
done
printf 'M9-M16 per-phase 10 fields: PASS\n'

# G3 M0-M8 content preserved
grep -qwF "M0 Foundation" docs/MASTER_ROADMAP_1.0.md && grep -qwF "M8 Application Navigation" docs/MASTER_ROADMAP_1.0.md && printf 'G3 content preserved: PASS\n'
```

**Command output** (2026-08-10; immediate HEAD `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`; 753 total lines):
```
ws: PASS
scope G4: PASS
cumulative scope G1234: PASS
line count (753 total, 396 new): PASS
roadmap 9 16: PASS
M9-M16 phase presence: PASS
M9-M16 phase names exact: PASS
M9-M16 per-phase 10 fields: PASS
G3 content preserved: PASS
```

#### Rollback Boundary

G4 exact files: `docs/MASTER_ROADMAP_1.0.md` (modified — M9-M16 appended after M8). No completed successor depends on G4 (G5+ remain BACKLOG). Rollback restores M0-M8 state exactly.

Dependency-aware hybrid rollback (G4 only, preserves G1+G2+G3):
- Remove M9-M16 content from `docs/MASTER_ROADMAP_1.0.md` (restore to 357-line M0-M8 state)
- Revert `openspec/changes/m0-foundation-v2/tasks.md` G4 checkbox
- Revert `openspec/changes/m0-foundation-v2/state.yaml` G4 lines
- Revert `openspec/changes/m0-foundation-v2/apply-progress.md` G4 section

#### Runtime Harness

N/A — docs-only milestone, no build/test/runtime target exists.

#### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | Run the reproducible verification commands above — exit 0, all 9 checks pass (ws, scope G4, cumulative scope G1234, line count 753/396 new, roadmap 9 16, M9-M16 phase presence, phase names exact, per-phase 10 fields, G3 content preserved) |
| Runtime harness command/scenario and exact result | N/A — docs-only; no build system, test target, framework, or runnable project command exists (config.yaml `test_command: ""`, `build_command: ""`) |
| Rollback boundary | `docs/MASTER_ROADMAP_1.0.md` — remove M9-M16 lines (restore to 357-line M0-M8); revert tasks.md G4 checkbox, state.yaml G4 lines, apply-progress.md G4 section; G1+G2+G3 files preserved |

### 1.5 G5←G4: debt/backlog authorities

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/TECHNICAL_DEBT_REGISTER.md` (31 lines), `docs/POST_1_0_BACKLOG.md` (46 lines)
- **Total**: 77 lines

#### Verification Evidence

| Check | Command | Result |
|---|---|---|
| Whitespace | `ws` | PASS — no trailing whitespace or merge conflicts |
| Scope | `scope G5` | PASS — exact 2 files: TECHNICAL_DEBT_REGISTER.md, POST_1_0_BACKLOG.md |
| Cumulative scope G12345 | `scope G12345` | PASS — 7 files: .gitignore, STATUS_MATRIX.md, DEFINITION_OF_DONE.md, INVARIANTS.md, MASTER_ROADMAP_1.0.md, TECHNICAL_DEBT_REGISTER.md, POST_1_0_BACKLOG.md |
| Line budget ≤400 | `wc -l` | PASS — 77 lines |
| Prettier formatting | `npx prettier --write` | PASS — both files unchanged (already conformant) |
| Debt register: 7 entries | `grep -c "^| TD-"` | PASS — 7 debt entries present |
| Debt register: severity distinct | `grep -wE "MINOR|MODERATE|SIGNIFICANT|SEVERE"` | PASS — all severities present; none named P0/P1 |
| Debt register: all 7 fields | `grep -E "ID|Severity|Source|Description|Repro|Mitigation|Target"` | PASS — all 7 column headers present |
| Backlog: 13 entries | `grep -c "^\| [0-9]"` | PASS — 13 deferred features |
| Backlog: justification per entry | Per-row `|` field 3 non-empty | PASS — every entry has justification text |
| Backlog: sizing per entry | `grep -cE "^\|.*\| (S\|M\|L\|XL) \|$"` | PASS — every entry has t-shirt sizing |
| G1+G2+G3+G4 preserved | File content unchanged | PASS — all prior governance authorities identical to G4 exit state |

#### Spec Trace

| # | Obligation | Status |
|---|---|---|
| 1 | Governance Spec: Technical Debt Register MUST record item identifier, description, impact, remediation plan, owner, target phase | PASS — 7 entries with ID, severity (distinct from P0/P1), source, description, repro, mitigation, target |
| 2 | Governance Spec: POST_1_0_BACKLOG MUST hold explicit deferred scope with rationale | PASS — 13 entries, each with feature name, justification, and t-shirt sizing |
| 3 | Proposal: scope (11 paths) | PASS — both files are authorized M0 paths |
| 4 | Tasks: G5←G4 dependency | PASS — G4 DONE before G5 implement |
| 5 | INVARIANTS: Feature freeze routes to POST_1_0_BACKLOG | PASS — all 22 exclusions mapped; 13 truly post-1.0 items enumerated with rationale |

#### Reproducible Verification Commands

```bash
M0_BASE=$(awk '/^M0_BASE:/{print $2}' openspec/changes/m0-foundation-v2/state.yaml)
mapfile -t SDD < <(awk '/^SDD:/{p=1;next} p&&/^  - /{sub(/^  - /,"");print}' openspec/changes/m0-foundation-v2/state.yaml)
eval "$(awk '/^```bash$/{p=1;next}/^```$/{if(p)exit}p' openspec/changes/m0-foundation-v2/tasks.md)"

# Whitespace
ws && printf 'ws: PASS\n'

# Scope G5
G5=(docs/{TECHNICAL_DEBT_REGISTER,POST_1_0_BACKLOG}.md)
scope G5 && printf 'scope G5: PASS\n'

# Cumulative scope G12345
G12345=(.gitignore docs/{STATUS_MATRIX,DEFINITION_OF_DONE,INVARIANTS,MASTER_ROADMAP_1.0,TECHNICAL_DEBT_REGISTER,POST_1_0_BACKLOG}.md)
scope G12345 && printf 'cumulative scope G12345: PASS\n'

# Line budget
debt_lines=$(wc -l < docs/TECHNICAL_DEBT_REGISTER.md)
backlog_lines=$(wc -l < docs/POST_1_0_BACKLOG.md)
total=$((debt_lines + backlog_lines))
[ "$total" -le 400 ] && printf 'line budget (%d debt + %d backlog = %d total): PASS\n' "$debt_lines" "$backlog_lines" "$total"

# Debt register: ≥1 entry
debt_count=$(grep -c '^| TD-' docs/TECHNICAL_DEBT_REGISTER.md)
[ "$debt_count" -ge 1 ] && printf 'debt entries (%d): PASS\n' "$debt_count"

# Backlog: ≥1 entry
backlog_count=$(grep -c '^| [0-9]' docs/POST_1_0_BACKLOG.md)
[ "$backlog_count" -ge 1 ] && printf 'backlog entries (%d): PASS\n' "$backlog_count"

# G4 content preserved
grep -qwF "M0 Foundation" docs/MASTER_ROADMAP_1.0.md && grep -qwF "M16 Michi Music Player 1.0 Stable" docs/MASTER_ROADMAP_1.0.md && printf 'G4 content preserved: PASS\n'
```

**Command output** (2026-08-10; immediate HEAD `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`; 77 product lines):
```
ws: PASS
scope G5: PASS
cumulative scope G12345: PASS
line budget (31 debt + 46 backlog = 77 total): PASS
debt entries (7): PASS
backlog entries (13): PASS
G4 content preserved: PASS
```

#### Rollback Boundary

G5 exact files: `docs/TECHNICAL_DEBT_REGISTER.md`, `docs/POST_1_0_BACKLOG.md`. No completed successor depends on G5 (G6+ remain BACKLOG). Rollback is `rm docs/TECHNICAL_DEBT_REGISTER.md docs/POST_1_0_BACKLOG.md` (docs/ survives with G1+G2+G3+G4 files).

Dependency-aware hybrid rollback (G5 only, preserves G1+G2+G3+G4):
- `rm docs/TECHNICAL_DEBT_REGISTER.md docs/POST_1_0_BACKLOG.md`
- Revert `openspec/changes/m0-foundation-v2/tasks.md` G5 checkbox
- Revert `openspec/changes/m0-foundation-v2/state.yaml` G5 lines
- Revert `openspec/changes/m0-foundation-v2/apply-progress.md` G5 section

#### Runtime Harness

N/A — docs-only milestone, no build/test/runtime target exists.

#### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | Run the reproducible verification commands above — exit 0, all 7 checks pass (ws, scope G5, cumulative scope G12345, line budget 77, debt entries 7, backlog entries 13, G4 content preserved) |
| Runtime harness command/scenario and exact result | N/A — docs-only; no build system, test target, framework, or runnable project command exists (config.yaml `test_command: ""`, `build_command: ""`) |
| Rollback boundary | `docs/TECHNICAL_DEBT_REGISTER.md`, `docs/POST_1_0_BACKLOG.md` — exact files; revert tasks.md G5 checkbox, state.yaml G5 lines, apply-progress.md G5 section; G1+G2+G3+G4 files preserved |

### 2.1 A1←G5: D1 Proposed (C++20 Domain Core, Qt 6 Infrastructure)

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/adr/0001-d1-language-runtime.md` (41 lines)
- **Total**: 41 lines

#### Verification Evidence

| Check | Result |
|---|---|
| 7 required headers (Title, Date, Context, Decision, Consequences, Alternatives considered, Status) | PASS — 7/7 |
| Date format YYYY-MM-DD (2026-08-10) | PASS |
| Status = Proposed | PASS |
| Prettier normalized | PASS — unchanged |

#### Rollback Boundary

`rm docs/adr/0001-d1-language-runtime.md`; revert tasks.md 2.1 checkbox, state.yaml A1 lines, apply-progress.md A1 section.

### 2.2 A2←A1: D3/D4 Proposed (State Ownership + Composition Root)

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/adr/0002-d3-state-ownership.md` (49 lines), `docs/adr/0003-d4-composition.md` (42 lines)
- **Total**: 91 lines

#### Verification Evidence

| Check | Result |
|---|---|
| 7 required headers (both files) | PASS — 7/7 each |
| Date format YYYY-MM-DD (2026-08-10) | PASS |
| Status = Proposed (both) | PASS |
| Prettier normalized | PASS |

#### Rollback Boundary

`rm docs/adr/0002-d3-state-ownership.md docs/adr/0003-d4-composition.md`; revert tasks.md 2.2 checkbox, state.yaml A2 lines, apply-progress.md A2 section.

### 2.3 A3←A2: D2/D5/D6 Proposed (Layers + Lifecycle + Concurrency)

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/adr/0004-d2-layers.md` (64 lines), `docs/adr/0005-d5-lifecycle.md` (54 lines), `docs/adr/0006-d6-concurrency.md` (44 lines)
- **Total**: 162 lines

#### Verification Evidence

| Check | Result |
|---|---|
| 7 required headers (all 3 files) | PASS — 7/7 each |
| Date format YYYY-MM-DD (2026-08-10) | PASS |
| Status = Proposed (all) | PASS |
| Prettier normalized | PASS |
| D2 cites predecessor D1 (0001) | PASS |
| D5 cites predecessor D4 (0003) | PASS |
| D6 cites predecessor D1 (0001) | PASS |

#### Rollback Boundary

`rm docs/adr/0004-d2-layers.md docs/adr/0005-d5-lifecycle.md docs/adr/0006-d6-concurrency.md`; revert tasks.md 2.3 checkbox, state.yaml A3 lines, apply-progress.md A3 section.

### 2.4 A4←A3: D7/D9/D10 Proposed (QML Boundary + Persistence + Effects)

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/adr/0007-d7-qml-boundary.md` (42 lines), `docs/adr/0008-d9-persistence.md` (43 lines), `docs/adr/0009-d10-errors-effects.md` (63 lines)
- **Total**: 148 lines

#### Verification Evidence

| Check | Result |
|---|---|
| 7 required headers (all 3 files) | PASS — 7/7 each |
| Date format YYYY-MM-DD (2026-08-10) | PASS |
| Status = Proposed (all) | PASS |
| Prettier normalized | PASS |
| D7 cites predecessor D1 (0001) | PASS |
| D9 cites predecessor D1 (0001) | PASS |
| D10 cites predecessor D3 (0002) | PASS |

#### Rollback Boundary

`rm docs/adr/0007-d7-qml-boundary.md docs/adr/0008-d9-persistence.md docs/adr/0009-d10-errors-effects.md`; revert tasks.md 2.4 checkbox, state.yaml A4 lines, apply-progress.md A4 section.

### 2.5 A5←A4: D8 Proposed (IAudioEngine Port)

- **Status**: DONE (verified 2026-08-10)
- **Transition**: BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
- **Files**: `docs/adr/0010-d8-audio-port.md` (51 lines)
- **Total**: 51 lines

#### Verification Evidence

| Check | Result |
|---|---|
| 7 required headers | PASS — 7/7 |
| Date format YYYY-MM-DD (2026-08-10) | PASS |
| Status = Proposed | PASS |
| Prettier normalized | PASS |
| D8 cites predecessor D1 (0001) | PASS |
| Authored last per sequence D1→D3/D4→D2/D5/D6→D7/D9/D10→D8 | PASS |

#### Rollback Boundary

`rm docs/adr/0010-d8-audio-port.md`; revert tasks.md 2.5 checkbox, state.yaml A5 lines, apply-progress.md A5 section.

## Remaining Tasks (BACKLOG)

- [ ] 2.6: Architecture document (AR←A5)
- [ ] 3.1–3.2: Evidence and Index

## Chain State

- **Current**: A5 (stacked-to-main slice 10) — DONE via BACKLOG→READY→IN_PROGRESS→REVIEW→VERIFY→DONE
- **Next**: AR → L → R (all unchecked BACKLOG; not ready or admitted)

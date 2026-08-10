# Tasks: M0 Foundation v2

## Review Workload Forecast

Forecast: ~2,900 total; G1=114(actual),G2=170(actual),G3~200,G4~180,G5~260,A1~100,A2~180,A3~270,A4~270,A5~90,AR~300,L~350,R~100; slices <=400.
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High
Delivery strategy: auto-chain

## Verification

```bash
G1=(.gitignore docs/STATUS_MATRIX.md);G2=(docs/{DEFINITION_OF_DONE,INVARIANTS}.md);G12=(.gitignore docs/{STATUS_MATRIX,DEFINITION_OF_DONE,INVARIANTS}.md);G3=(docs/MASTER_ROADMAP_1.0.md);G4=(docs/MASTER_ROADMAP_1.0.md);G5=(docs/{TECHNICAL_DEBT_REGISTER,POST_1_0_BACKLOG}.md)
A1=(docs/adr/0001-d1-language-runtime.md);A2=(docs/adr/{0002-d3-state-ownership,0003-d4-composition}.md);A3=(docs/adr/{0004-d2-layers,0005-d5-lifecycle,0006-d6-concurrency}.md);A4=(docs/adr/{0007-d7-qml-boundary,0008-d9-persistence,0009-d10-errors-effects}.md);A5=(docs/adr/0010-d8-audio-port.md)
AR=(docs/ARCHITECTURE.md);L=(docs/MIGRATION_LEDGER.md);R=(README.md);P=(README.md .gitignore docs);B=(openspec/changes/m0-foundation-v2/{apply-progress.md,state.yaml});O=(README.md .gitignore docs/{STATUS_MATRIX,DEFINITION_OF_DONE,INVARIANTS,MASTER_ROADMAP_1.0,TECHNICAL_DEBT_REGISTER,POST_1_0_BACKLOG,ARCHITECTURE,MIGRATION_LEDGER}.md docs/adr/{0001-d1-language-runtime,0002-d3-state-ownership,0003-d4-composition,0004-d2-layers,0005-d5-lifecycle,0006-d6-concurrency,0007-d7-qml-boundary,0008-d9-persistence,0009-d10-errors-effects,0010-d8-audio-port}.md);E=runtime:N/A-docs-only,rollback:array-path
changed(){ local b=${1:-HEAD};{ git diff --name-only "$b" --;git ls-files --others --exclude-standard;git ls-files --others -i --exclude-standard;}|LC_ALL=C sort -u; }
ws(){ git diff --check HEAD -- "${P[@]}"||return;for f in $(git ls-files --others --exclude-standard -- "${P[@]}");do git diff --no-index --check /dev/null "$f";[ $? -le 1 ]||return;done; }
scope(){ local -n u=$1;diff -u <(LC_ALL=C comm -23 <(changed) <(printf '%s\n' "${SDD[@]}" "${B[@]}"|LC_ALL=C sort -u)) <(printf '%s\n' "${u[@]}"|LC_ALL=C sort -u); }
repo(){ { git diff --name-only "$M0_BASE" --;git ls-files --others;}|LC_ALL=C sort -u; }
scope_all(){ git cat-file -e "$M0_BASE^{commit}"&&diff -u <(LC_ALL=C comm -23 <(repo) <(printf '%s\n' "${SDD[@]}"|LC_ALL=C sort -u)) <(printf '%s\n' "${O[@]}"|LC_ALL=C sort -u); }
roadmap(){ for m in $(seq "$1" "$2");do grep -qw "M$m" docs/MASTER_ROADMAP_1.0.md||return;done;for f in Objective Scope Out-of-scope Dependencies Deliverables New-test Entry Exit Acceptance Risks;do grep -Eqi "(^|[^[:alnum:]_])$f([^[:alnum:]_]|$)" docs/MASTER_ROADMAP_1.0.md||return;done; }
C=UNKNOWN,AUDITED,BROKEN,PARTIAL,FUNCTIONAL,TESTED,STABLE,FROZEN;W=BACKLOG,READY,IN_PROGRESS,REVIEW,VERIFY,BLOCKED,DONE,DEFERRED;I='.DS_Store,Thumbs.db,desktop.ini,$RECYCLE.BIN/,*.swp,*.swo,*~,.vscode/,.idea/,*.sublime-*,.project,.classpath,.settings/,.env*,*.log'
component_states(){ awk '/^## Component State Machine$/{p=1}/^## Work-Package State Machine$/{p=0}p&&/^\| [A-Z_]+ \|/{print $2}' docs/STATUS_MATRIX.md;}
wp_states(){ awk '/^## Work-Package State Machine$/{p=1}p&&/^\| [A-Z_]+ \|/{print $2}' docs/STATUS_MATRIX.md;}
states(){ [ "$(component_states|paste -sd,)" = "$C" ]&&[ "$(wp_states|paste -sd,)" = "$W" ];}
transitions(){ grep -qE '^UNKNOWN[[:space:]]*→[[:space:]]*AUDITED[[:space:]]*→[[:space:]]*FUNCTIONAL[[:space:]]*→[[:space:]]*TESTED[[:space:]]*→[[:space:]]*STABLE[[:space:]]*→[[:space:]]*FROZEN$' docs/STATUS_MATRIX.md&&grep -qE '^BACKLOG[[:space:]]*→[[:space:]]*READY[[:space:]]*→[[:space:]]*IN_PROGRESS[[:space:]]*→[[:space:]]*REVIEW[[:space:]]*→[[:space:]]*VERIFY[[:space:]]*→[[:space:]]*DONE$' docs/STATUS_MATRIX.md||return;for s in BROKEN PARTIAL;do grep -qE "\`$s[[:space:]]*→[[:space:]]*FUNCTIONAL\`" docs/STATUS_MATRIX.md||return;done;for s in READY IN_PROGRESS REVIEW VERIFY;do grep -qE "^-[[:space:]]+\`$s[[:space:]]*→[[:space:]]*BLOCKED\`[[:space:]]+resumes[[:space:]]+as[[:space:]]+\`$s\`$" docs/STATUS_MATRIX.md||return;done;for s in BACKLOG READY BLOCKED;do grep -qE "^-[[:space:]]+\`$s[[:space:]]*→[[:space:]]*DEFERRED\`$" docs/STATUS_MATRIX.md||return;done;grep -qE '^`DEFERRED[[:space:]]*→[[:space:]]*BACKLOG`[[:space:]]+SHALL[[:space:]]+occur[[:space:]]+only[[:space:]]+after[[:space:]]+an[[:space:]]+approved[[:space:]]+scope[[:space:]]+change\.' docs/STATUS_MATRIX.md;}
stack_neutral(){ [ "$(grep -Ev '^\s*(#|$)' .gitignore|paste -sd,)" = "$I" ];}
ledger(){ for f in ID capability/responsibility Legacy[ ]source functional[ ]description Legacy[ ]state Legacy[ ]dependencies known[ ]problems decision justification new[ ]destination new[ ]contract Legacy[ ]tests[ ]found new[ ]tests[ ]required migration[ ]state risks technical[ ]debt frozen;do grep -Eqi "$f" docs/MIGRATION_LEDGER.md||return;done; }
adr(){ local -n a=$1;for f in "${a[@]}";do [ "$(grep -Ec '^## (Title|Date|Context|Decision|Consequences|Alternatives considered|Status)$' "$f")" -eq 7 ]||return;grep -A2 '^## Date$' "$f"|grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'||return;grep -A2 '^## Status$' "$f"|grep -qx Proposed||return;done; }
links(){ command -v lychee>/dev/null&&{ lychee README.md docs/*.md docs/adr/*.md;return;};python3 -c 'import pathlib,re,sys,urllib.parse as u
for f in map(pathlib.Path,sys.argv[1:]):
 for x in re.findall(r"!?\[[^]]*\]\(([^ )]+)",f.read_text()):
  y=u.unquote(x.strip("<>").split("#")[0]);assert not y or u.urlsplit(y).scheme or y.startswith("//") or (f.parent/y).exists(),f"{f}: {x}"' README.md docs/*.md docs/adr/*.md; }
```

Chain: G1→G2→G3→G4→G5→A1→A2→A3→A4→A5→AR→L→R. Slice: command+trace+rollback; G4 preserves G3; sync Apply; final `scope_all`.

## Governance

- [x] [BACKLOG→READY→IN_PROGRESS→REVIEW→VERIFY→DONE] 1.1 G1: ignore/status; `ws&&scope G1&&states&&transitions&&stack_neutral`; `$E`; 114 lines, 5/5 PASS (2026-08-10).
- [x] [BACKLOG→READY→IN_PROGRESS→REVIEW→VERIFY→DONE] 1.2 G2←G1: DoR/DoD/Golden Path/invariants; `ws&&scope G12`; `$E`; 170 lines; independent gate PASS (authoritative content, parity, cumulative scope, rollback, G1 preserved, G3+ BACKLOG).
- [x] [BACKLOG→READY→IN_PROGRESS→REVIEW→VERIFY→DONE] 1.3 G3←G2: M0-M8; `ws&&roadmap 0 8`; `$E`; 357 lines; all 9 phases (M0-M8) present, 10 fields per phase, phase names exact; cumulative scope G123 PASS (uncommitted chain).
- [ ] [BACKLOG] 1.4 G4←G3: M9-M16; `ws&&scope G4&&roadmap 9 16`; `$E`.
- [ ] [BACKLOG] 1.5 G5←G4: debt/backlog; `ws&&scope G5`; `$E`.

## Architecture

- [ ] [BACKLOG] 2.1 A1←G5: D1 Proposed; `ws&&scope A1&&adr A1`; `$E`.
- [ ] [BACKLOG] 2.2 A2←A1: D3/D4 Proposed; `ws&&scope A2&&adr A2`; `$E`.
- [ ] [BACKLOG] 2.3 A3←A2: D2/D5/D6 Proposed; `ws&&scope A3&&adr A3`; `$E`.
- [ ] [BACKLOG] 2.4 A4←A3: D7/D9/D10 Proposed; `ws&&scope A4&&adr A4`; `$E`.
- [ ] [BACKLOG] 2.5 A5←A4: D8 Proposed; `ws&&scope A5&&adr A5`; `$E`.
- [ ] [BACKLOG] 2.6 AR←A5: architecture; `ws&&scope AR`; `$E`.

## Evidence

- [ ] [BACKLOG] 3.1 L←AR: ledger@`63914a00`; `ws&&scope L&&ledger`; `$E`.
- [ ] [BACKLOG] 3.2 R←L: index; `ws&&scope R&&links`; `$E`.

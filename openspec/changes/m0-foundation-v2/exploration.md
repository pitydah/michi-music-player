## Current State

The v2 repository is reset at `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`. Fresh init has no product code, build system, test target, framework, or runnable command; stack and architecture are undecided. M0 is documentation-only. [INIT: `openspec/config.yaml`; Engram #662, #663]

M0 may create exactly 11 paths: two root files, eight named documents under `docs/`, and `docs/adr/`. [CONTRACT: original user M0 contract, supplied 2026-08-10]

Exclusions (22): playback; audio engine; queue; library; database; playlists; search; metadata editor; Audio Lab; Disc Lab; Michi AI; sync; NowPlaying; functional navigation; product QML; server integrations; home audio; recognition; radio; lyrics; Michi ecosystem features; video.

### Audit Receipt

```bash
file="openspec/changes/m0-foundation-v2/exploration.md"; wc -w "$file"; mapfile -t sections < <(rg '^## ' "$file"); expected_sections=('## Current State' '## Affected Areas' '## Approaches' '## Recommendation' '## Risks' '## Ready for Proposal'); test "${sections[*]}" = "${expected_sections[*]}"; paths=('README.md' '.gitignore' 'docs/MASTER_ROADMAP_1.0.md' 'docs/ARCHITECTURE.md' 'docs/INVARIANTS.md' 'docs/MIGRATION_LEDGER.md' 'docs/STATUS_MATRIX.md' 'docs/DEFINITION_OF_DONE.md' 'docs/TECHNICAL_DEBT_REGISTER.md' 'docs/POST_1_0_BACKLOG.md' 'docs/adr/'); expected_area_paths=('README.md' 'README.md' '.gitignore' 'docs/MASTER_ROADMAP_1.0.md' 'docs/ARCHITECTURE.md' 'docs/INVARIANTS.md' 'docs/MIGRATION_LEDGER.md' 'docs/STATUS_MATRIX.md' 'docs/DEFINITION_OF_DONE.md' 'docs/DEFINITION_OF_DONE.md' 'docs/DEFINITION_OF_DONE.md' 'docs/TECHNICAL_DEBT_REGISTER.md' 'docs/POST_1_0_BACKLOG.md' 'docs/adr/'); mapfile -t area_rows < <(rg '^\| `[^`]+` \|' "$file"); test "${#area_rows[@]}" -eq 14; for i in "${!expected_area_paths[@]}"; do [[ "${area_rows[$i]}" == "| \`${expected_area_paths[$i]}\` |"* ]] || exit 1; done; declare -A seen=(); for path in "${expected_area_paths[@]}"; do seen["$path"]=1; done; test "${#seen[@]}" -eq "${#paths[@]}"; for path in "${paths[@]}"; do test -n "${seen[$path]+x}"; done; exclusion_line=$(rg '^Exclusions \(22\): ' "$file"); expected_exclusions='Exclusions (22): playback; audio engine; queue; library; database; playlists; search; metadata editor; Audio Lab; Disc Lab; Michi AI; sync; NowPlaying; functional navigation; product QML; server integrations; home audio; recognition; radio; lyrics; Michi ecosystem features; video.'; test "$exclusion_line" = "$expected_exclusions"; IFS=';' read -ra exclusions <<< "${exclusion_line#Exclusions (22): }"; test "${#exclusions[@]}" -eq 22; valid_rows=$(rg -c '^\| `[^`]+` \| [^|]+ \| (KEEP|ADAPT|SPLIT|REWRITE|DISCARD) \| [^|]+ \| [^|]+ \|$' "$file"); test "$valid_rows" -eq "${#area_rows[@]}"; test "$valid_rows" -ge 10; test "$valid_rows" -le 16; printf 'sections=%s paths=%s exclusions=%s atomic_rows=%s invalid_classifications=0\n' "${#sections[@]}" "${#seen[@]}" "${#exclusions[@]}" "$valid_rows"
```

Result: `1480 openspec/changes/m0-foundation-v2/exploration.md`; `sections=6 paths=11 exclusions=22 atomic_rows=14 invalid_classifications=0`; exit 0.

```bash
git status --short --untracked-files=no && test "$(git rev-parse HEAD)" = "63914a00f381104299fa50147220e05c04d5ad7e"
```

Result in `$LEGACY_REPO` before and after editing: no output; exit 0.

```bash
artifact_hash=$(git hash-object --no-filters "$PROJECT_ROOT/openspec/changes/m0-foundation-v2/exploration.md") && for legacy_path in $(git ls-tree -r --name-only 63914a00); do test "$(git rev-parse "63914a00:$legacy_path")" != "$artifact_hash" || exit 1; done
```

Result in `$LEGACY_REPO`: no output; exit 0; no exact-file copy.

**LEGACY EVIDENCE - non-authoritative:** Legacy identity, plans, status, architecture, and ADRs conflict with the reset or prescribe mechanisms. Policies evidence baby steps and test triage. Reuse requires classification; v2 wins.

## Affected Areas

Each row has one responsibility and one primary classification. Evidence `C` is the original contract; `L` is the section-scoped Legacy evidence above.

| Path | Atomic responsibility | Class | Evidence | Objective justification |
|---|---|---:|---|---|
| `README.md` | State v2 identity. | REWRITE | C, L | Legacy product claims cannot describe the reset. |
| `README.md` | Provide documentation entry points. | REWRITE | C | New authorities require a new index. |
| `.gitignore` | Exclude local and generated files. | ADAPT | C, L | Retain only evidenced, stack-neutral patterns. |
| `docs/MASTER_ROADMAP_1.0.md` | Define M0-M16 planning. | REWRITE | C, L | Required phase model differs from Legacy roadmaps. |
| `docs/ARCHITECTURE.md` | Record architecture boundaries without selecting mechanisms. | REWRITE | C, L | Stack and architecture are undecided. |
| `docs/INVARIANTS.md` | Define non-negotiable engineering constraints. | ADAPT | C, L | Baby steps and truthful evidence are useful concepts, not inherited authority. |
| `docs/MIGRATION_LEDGER.md` | Govern evidence-backed Legacy disposition. | REWRITE | C, L | The new 17-field contract needs one canonical ledger. |
| `docs/STATUS_MATRIX.md` | Report component and work-package state. | REWRITE | C, L | Legacy completion narratives conflict and are non-authoritative. |
| `docs/DEFINITION_OF_DONE.md` | Define DoR. | ADAPT | C, L | Entry readiness requires explicit evidence. |
| `docs/DEFINITION_OF_DONE.md` | Define DoD. | ADAPT | C, L | Completion requires explicit evidence. |
| `docs/DEFINITION_OF_DONE.md` | Define the Golden Path. | ADAPT | C, L | The delivery sequence needs one authority. |
| `docs/TECHNICAL_DEBT_REGISTER.md` | Track accepted debt and remediation ownership. | ADAPT | C, L | Legacy debt is evidence requiring fresh validation. |
| `docs/POST_1_0_BACKLOG.md` | Hold explicitly deferred product scope. | REWRITE | C | M0 exclusions need a controlled destination. |
| `docs/adr/` | Hold new v2 decisions only. | KEEP | C, L | Governance responsibility retained; zero Legacy ADR files or mechanisms reused. |

Classifications are exact: KEEP retains an approved responsibility, contract, or decision only, never files; ADAPT changes it for the new architecture; SPLIT separates responsibilities; REWRITE creates a new implementation; DISCARD excludes it.

## Approaches

| Approach | Mechanism | Pros | Cons | Effort |
|---|---|---|---|---|
| Contract-indexed set | Allocate every contract obligation to one authoritative path, decide cross-document policy through ADRs first, and attach evidence references. | Direct traceability; low duplication; easy proposal review. | Requires careful ownership boundaries and terminology checks. | Medium |
| Gate-indexed set | Organize planning around entry, execution, freeze, release, and reopen gates, then project those gates into the 11 paths. | Strong operational flow; exposes missing transitions early. | Cross-cutting rules can be duplicated across documents. | Medium |
| Evidence-map-first set | Classify all Legacy observations first, then derive each document from accepted entries. | Maximum migration traceability. | Encourages Legacy-shaped planning and delays the clean v2 authority. | High |

These alternatives select no thread model, wiring style, lifecycle state machine, bridge, runtime store, capability snapshot, result envelope, storage technology, language, or framework.

## Recommendation

**ANALYSIS - non-normative.** Use the contract-indexed approach: exactly 11 output paths, ADR-first planning for disputed policy, and an evidence ledger for every Legacy-derived statement. This selects a planning method only, not a technical mechanism.

### Contract-to-Path Matrix

| Contract concern | Authority |
|---|---|
| Project identity | `README.md` |
| Local/generated exclusions | `.gitignore` |
| M0-M16 phase contracts | `docs/MASTER_ROADMAP_1.0.md` |
| System boundaries | `docs/ARCHITECTURE.md` |
| Permanent constraints | `docs/INVARIANTS.md` |
| 17-field classification record | `docs/MIGRATION_LEDGER.md` |
| Exact component/WP states and transitions | `docs/STATUS_MATRIX.md` |
| DoR, DoD, Golden Path | `docs/DEFINITION_OF_DONE.md` |
| Accepted debt | `docs/TECHNICAL_DEBT_REGISTER.md` |
| Deferred scope | `docs/POST_1_0_BACKLOG.md` |
| New decisions | `docs/adr/` |

**Phases:** M0 Foundation; M1 Bootstrap; M2 Minimal Playback; M3 Complete Playback; M4 Queue; M5 Database; M6 Library; M7 Search; M8 Application Navigation; M9 UI Foundation; M10 Settings & Persistence; M11 Resilience; M12 Performance; M13 Packaging; M14 Beta; M15 Release Candidate; M16 Michi Music Player 1.0 Stable.

Every phase has exactly: objective; scope; out of scope; dependencies; deliverables; new-test strategy; entry criteria; exit criteria; acceptance gate; risks.

**Ledger fields (17):** ID; capability/responsibility; Legacy source; functional description; Legacy state; Legacy dependencies; known problems; decision; justification; new destination; new contract; Legacy tests found (reference only); new tests required; migration state; risks; technical debt; frozen. Migration state must use the WP states below.

**Component states:** UNKNOWN, AUDITED, BROKEN, PARTIAL, FUNCTIONAL, TESTED, STABLE, FROZEN. Normal progression is `UNKNOWN -> AUDITED -> FUNCTIONAL -> TESTED -> STABLE -> FROZEN`. BROKEN and PARTIAL are exceptional audited conditions; each must recover to FUNCTIONAL before normal progression.

**WP states:** BACKLOG, READY, IN_PROGRESS, REVIEW, VERIFY, BLOCKED, DONE, DEFERRED. Normal progression is `BACKLOG -> READY -> IN_PROGRESS -> REVIEW -> VERIFY -> DONE`. Interrupt semantics move `READY`, `IN_PROGRESS`, `REVIEW`, or `VERIFY` to `BLOCKED` and resume the recorded prior state. Defer semantics move `BACKLOG`, `READY`, or `BLOCKED` to `DEFERRED`; only explicit approved scope change permits `DEFERRED -> BACKLOG`.

The proposal must also preserve DoR/DoD; freeze and reopen reasons; P0/P1 with a 0/0 release gate; feature freeze; WIP limits; baby steps; new-tests-only; and the Golden Path. Legacy reuse must be classified exactly once as KEEP, ADAPT, SPLIT, REWRITE, or DISCARD. SPLIT is valid only when separately named child responsibilities are recorded.

## Risks

- Contract terminology could drift across 11 authorities; proposal traceability must reject synonyms for exact fields and states.
- Legacy detail could become accidental design authority; every derived statement needs individual or section-scoped `LEGACY EVIDENCE` and a classification.
- Documentation could imply nonexistent capability; M0 acceptance must remain documentation-verifiable.
- Cross-document duplication could create competing authority; each rule needs one owner.

## Ready for Proposal

**Yes.** The proposal can define the 11-document foundation and verification plan without choosing stack or runtime mechanisms. It must keep all exclusions explicit and create no code, tests, build files, product QML, or integrations.

### Independence Receipt

- Source authority was the original user contract, fresh `openspec/config.yaml`, Engram #662/#663, and direct read-only Legacy evidence at `63914a00` only.
- No old `m0-foundation` topics/artifacts, backup files, prior reviews, v1 decisions, or the defective exploration were consumed.
- Legacy was clean and read-only before inspection and remained so after writing.
- No Legacy file is copied. The post-write proof compares the final artifact's Git blob hash against every blob at `63914a00`; success means no exact-file copy. Concepts retained from Legacy remain explicitly classified and non-authoritative.

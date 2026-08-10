# Governance Specification

## Purpose

Defines M0 governance authorities for planning,delivery,constraints,debt,deferral.

## Requirements

### Requirement: M0 Deliverables and Exclusions

M0 MUST create only 11 paths: README.md (project identity/governance index); .gitignore (stack-neutral; OS/editor/environment artifacts only; MUST NOT assume framework/language/build system); docs/MASTER_ROADMAP_1.0.md;docs/ARCHITECTURE.md;docs/INVARIANTS.md;docs/MIGRATION_LEDGER.md;docs/STATUS_MATRIX.md;docs/DEFINITION_OF_DONE.md;docs/TECHNICAL_DEBT_REGISTER.md;docs/POST_1_0_BACKLOG.md;docs/adr/. M0 MUST NOT create product artifacts: product code,tests,build files,src/,qml/,product QML,integrations,runtime behavior. Exclusions (22): playback;audio engine;queue;library;database;playlists;search;metadata editor;Audio Lab;Disc Lab;Michi AI;sync;NowPlaying;functional navigation;product QML;server integrations;home audio;recognition;radio;lyrics;Michi ecosystem features;video.

#### Scenario: Output
- GIVEN M0 completion
- WHEN workspace inspected
- THEN 11 paths exist; prohibited product artifacts do not

#### Scenario: Exclusions
- GIVEN M0 scope
- WHEN exclusion attempted
- THEN rejection routes it to POST_1_0_BACKLOG or future phase

#### Scenario: README
- GIVEN README.md
- WHEN inspected
- THEN project identity and all governance-authority links exist

#### Scenario: .gitignore
- GIVEN .gitignore
- WHEN inspected
- THEN only OS/editor/environment artifacts are excluded; stack assumptions are absent

### Requirement: Master Roadmap

`docs/MASTER_ROADMAP_1.0.md` MUST cover M0–M16. Every phase MUST have non-empty: objective;scope;out-of-scope;dependencies;deliverables;new-test strategy;entry criteria;exit criteria;acceptance gate;risks. Each phase MUST route its new-test strategy; without one it MAY NOT proceed.

#### Scenario: Completeness
- GIVEN any phase
- WHEN inspected
- THEN ten fields are non-empty

#### Scenario: Test-routing
- GIVEN phase adding capability
- WHEN new-test strategy inspected
- THEN test layer,scope,coverage are named

### Requirement: Component State Machine

`docs/STATUS_MATRIX.md` MUST define exactly UNKNOWN,AUDITED,BROKEN,PARTIAL,FUNCTIONAL,TESTED,STABLE,FROZEN. Normal: `UNKNOWN → AUDITED → FUNCTIONAL → TESTED → STABLE → FROZEN`. Exceptional BROKEN/PARTIAL MUST recover to FUNCTIONAL before normal progression.

#### Scenario: Progression
- GIVEN AUDITED component
- WHEN functional criteria pass
- THEN transition is FUNCTIONAL

#### Scenario: Recovery
- GIVEN BROKEN component
- WHEN remediation passes
- THEN it MUST enter FUNCTIONAL,never TESTED

### Requirement: Work-Package State Machine

`docs/STATUS_MATRIX.md` MUST define exactly BACKLOG,READY,IN_PROGRESS,REVIEW,VERIFY,BLOCKED,DONE,DEFERRED. Normal: `BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE`. READY/IN_PROGRESS/REVIEW/VERIFY MAY enter BLOCKED and MUST resume the recorded prior state. BACKLOG/READY/BLOCKED MAY enter DEFERRED; `DEFERRED → BACKLOG` MUST require approved scope change.

#### Scenario: Flow
- GIVEN READY WP
- WHEN work starts
- THEN transition is IN_PROGRESS

#### Scenario: Blocking
- GIVEN IN_PROGRESS WP
- WHEN dependency blocks work
- THEN BLOCKED records IN_PROGRESS

#### Scenario: Deferral
- GIVEN DEFERRED WP
- WHEN BACKLOG requested
- THEN transition SHALL NOT occur without approved scope change

### Requirement: DoR, DoD, Golden Path

`docs/DEFINITION_OF_DONE.md` MUST define DoR,DoD,Golden Path. Before READY, DoR MUST verify scope clarity,acceptance criteria,resolved dependencies,estimated effort. Before DONE, DoD MUST verify acceptance criteria met,new tests pass,zero P0/P1 open,review approved. Golden Path MUST be the singular end-to-end delivery sequence; every phase MUST contribute one verifiable increment.

#### Scenario: DoR
- GIVEN BACKLOG WP
- WHEN DoR assessed
- THEN READY requires four DoR criteria

#### Scenario: DoD
- GIVEN VERIFY WP
- WHEN DoD assessed
- THEN DONE requires four DoD criteria

#### Scenario: Golden-Path
- GIVEN phase nearing exit
- WHEN Golden Path increment verified
- THEN phase MAY proceed to acceptance

### Requirement: Invariants

`docs/INVARIANTS.md` MUST record freeze reasons;reopen reasons;P0/P1 0/0 release gate;feature-freeze policy;WIP limits;baby-steps policy;new-tests-only policy. 0/0 gate MUST require zero P0/P1 before any release candidate. Feature freeze MUST prohibit new features without approved reopening exception. WIP limits MUST cap concurrent phase work. Baby steps MUST be minimal independently-verifiable changes. New-tests-only MUST require one passing test per behavioral change.

#### Scenario: Release
- GIVEN release candidate
- WHEN P0 > 0 or P1 > 0
- THEN release SHALL NOT proceed

#### Scenario: Freeze
- GIVEN active feature freeze
- WHEN new-feature WP proposed
- THEN it MUST be rejected without approved exception

### Requirement: Technical Debt Register

`docs/TECHNICAL_DEBT_REGISTER.md` MUST record item identifier;description;impact;remediation plan;owner;target phase.

#### Scenario: Debt
- GIVEN accepted technical debt
- WHEN entry inspected
- THEN six fields exist

### Requirement: Post-1.0 Backlog

`docs/POST_1_0_BACKLOG.md` MUST hold explicit deferred scope with rationale.

#### Scenario: Backlog
- GIVEN demanded feature excluded from 1.0
- WHEN backlog inspected
- THEN feature name and deferral rationale exist

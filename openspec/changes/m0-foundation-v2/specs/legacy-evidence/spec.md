# Legacy-Evidence Specification

## Purpose

Governs the disposition of Legacy evidence through a 17-field migration ledger. Every Legacy-derived claim is classified exactly once and labeled non-authoritative; v2 specifications always prevail. Zero-copy and read-only-test policies protect the clean workspace.

## Requirements

### Requirement: Migration Ledger Fields

The system MUST maintain `docs/MIGRATION_LEDGER.md` with exactly 17 fields per row: ID, capability/responsibility, Legacy source, functional description, Legacy state, Legacy dependencies, known problems, decision, justification, new destination, new contract, Legacy tests found (reference only), new tests required, migration state, risks, technical debt, frozen. No field MAY be omitted or merged.

#### Scenario: Field completeness

- GIVEN any ledger row
- WHEN inspected
- THEN all 17 fields are present and non-empty

### Requirement: Classification Rules

Each ledger row MUST carry exactly one classification: KEEP, ADAPT, SPLIT, REWRITE, or DISCARD. KEEP retains an approved responsibility, contract, or decision — never a file. ADAPT changes it for the new architecture. SPLIT separates it into named child responsibilities; children MUST be listed in the row. REWRITE creates a new implementation. DISCARD excludes it entirely. No row MAY carry more than one classification. SPLIT without named children SHALL be invalid.

#### Scenario: Single classification

- GIVEN any ledger row
- WHEN the classification field is read
- THEN exactly one of the five values is present

#### Scenario: SPLIT with children

- GIVEN a row classified as SPLIT
- WHEN inspected
- THEN named child responsibilities are listed

### Requirement: Legacy Evidence Labels

Every statement derived from Legacy sources MUST carry an individual or section-scoped `LEGACY EVIDENCE – non-authoritative` label. V2 specifications SHALL always prevail over any Legacy-derived claim in case of conflict.

#### Scenario: Label presence

- GIVEN a document section containing Legacy-derived content
- WHEN inspected
- THEN a LEGACY EVIDENCE label is present

#### Scenario: Authority resolution

- GIVEN a conflict between a Legacy-derived claim and a v2 specification
- WHEN the conflict is identified
- THEN the v2 specification prevails

### Requirement: Zero-Copy Policy

The system MUST NOT create, store, or reference any duplicate of a Legacy file within the v2 workspace. Every Legacy reference MUST point to the original source location at the read-only commit `63914a00`.

#### Scenario: Duplicate prevention

- GIVEN the v2 workspace
- WHEN searched for Legacy file copies
- THEN no file duplicates exist

### Requirement: Legacy Test Policy

Legacy tests found during migration SHALL be recorded in the ledger as reference-only entries. Legacy tests MUST NOT be executed, ported, or used as pass/fail criteria for new development. New behavioral evidence MUST require new tests written for the v2 context.

#### Scenario: Read-only reference

- GIVEN a ledger row with Legacy tests found
- WHEN the test strategy is defined
- THEN Legacy tests are listed as reference only and excluded from execution

#### Scenario: New evidence requirement

- GIVEN a capability migrated from Legacy
- WHEN new behavioral evidence is produced
- THEN it is accompanied by new tests in the v2 context

### Requirement: Migration State Binding

The migration state field in every ledger row MUST use exactly the WP states defined by the Governance specification. No custom or undefined state SHALL be used.

#### Scenario: State validity

- GIVEN any ledger row
- WHEN the migration state is inspected
- THEN it matches one of the eight WP states

# ADR 0005: SQLite settings persistence with health detection

## Title

Settings persist in a single SQLite database behind the `SettingsRepository` port, with read-only health inspection at startup.

## Date

2026-08-12

## Context

Settings persistence must survive restarts (volume, muted, last_directory, recent_files) and must never crash the application when the database file is missing, corrupt, locked, or malformed. The application layer must not depend on SQLite directly; storage is an infrastructure concern.

## Decision

- `SettingsRepository` (application port) abstracts load/save of `SettingsState`. `SQLiteSettingsRepository` (infrastructure) is the concrete implementation.
- Persistence is a single SQLite database in the platform app-data directory, opened with WAL mode.
- `SettingsService` is the sole owner of `SettingsState` and the only caller of `SettingsRepository` mutations; bootstrap and coordinators use its public API only.
- The read-only health-inspection capability (`inspect_path`, with extended-result-code normalization) is implemented and unit-tested (M11.2A), producing a `PersistenceHealth` classification: MISSING, HEALTHY, CORRUPT_DATABASE, MALFORMED_DATA, LOCKED, ACCESS_FAILURE, IO_FAILURE, UNKNOWN_FAILURE. Inspection never mutates the file. Wiring the inspection into the startup flow (before any write) is pending, scheduled with the recovery phases.
- Health outcomes drive behavior conservatively: healthy → normal load; anything else → explicit diagnostic, no destructive repair (repair is a future capability, M11.2B-E). Note: current `load()` has one localized tolerant fallback — malformed `recent_files` JSON logs a warning and resets to `[]`; other malformed fields propagate. M11.2C will unify field-recovery policy.
- Shutdown persistence is best-effort with first-error-wins reporting (see the lifecycle contract in ARCHITECTURE.md).

## Consequences

- Storage is swappable behind the port; tests use in-memory or temporary-file repositories.
- Once wired into startup, a corrupt database cannot crash startup: every failure mode has a typed diagnostic. The wiring is pending; the capability and its tests are in place (M11.2A).
- The health taxonomy is part of the domain contract (`PersistenceHealth` in domain, no Qt, no I/O).
- M11.2B (TESTED, capability only, no production consumer): the Last-Known-Good snapshot lives at `<db>.lkg`; only a HEALTHY primary may refresh it; the SQLite backup API is used (read-only source) so WAL-committed content is captured; the candidate is validated before atomic promotion and an existing LKG survives every failed refresh; recovery is STAGED into a new caller-supplied destination (never installed over the primary; the primary is never replaced, renamed, or repaired automatically); staging refuses to overwrite an existing destination (`FileExistsError`) and rejects primary/LKG aliases (`ValueError`); failed candidates are removed.
- Automatic startup recovery is NOT implemented; startup preflight is NOT implemented. Field-level malformed-data recovery policy (M11.2C) and startup/recovery orchestration (M11.2D) remain pending and will consume this capability.
- Repair actions (field repair, quarantine, safe mode) remain unimplemented by design; the taxonomy and the M11.2B capabilities are the contract they will build against.

## Alternatives considered

- **JSON file per settings blob**: human-readable and diffable, but fragile under partial writes and offers no integrity primitives. Rejected in favor of SQLite's transactional integrity and WAL.
- **QSettings (Qt-native)**: zero extra code, but platform-dependent storage locations and no typed health model. Rejected.
- **No persistence port (SQLite used directly in application)**: breaks layering (ADR 0002) and blocks headless testing. Rejected.

## Status

Accepted

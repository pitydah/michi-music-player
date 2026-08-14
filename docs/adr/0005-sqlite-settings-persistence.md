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
- Health outcomes drive behavior conservatively: healthy → normal load; anything else → explicit diagnostic, no destructive repair (repair is a future capability, M11.2D-E). M11.2C (TESTED) implements field-level malformed-data recovery: `load()` decodes each persisted field independently; a malformed value falls back to its domain default with one logged warning while valid sibling fields are preserved; no field is silently coerced; nothing is written back (safe read fallback, not repair). The canonical persisted `muted` representation is `"true"`/`"false"` (as written by `save()`), and `load()` and `inspect_path()` agree on it — non-canonical values such as `"1"`/`"0"` are malformed. `inspect_path()` remains strict: load tolerance is not database health, and `MALFORMED_DATA` remains a valid diagnosis for the same content; the startup reaction belongs to M11.2D.
- Shutdown persistence is best-effort with first-error-wins reporting (see the lifecycle contract in ARCHITECTURE.md).

## Consequences

- Storage is swappable behind the port; tests use in-memory or temporary-file repositories.
- Once wired into startup, a corrupt database cannot crash startup: every failure mode has a typed diagnostic. The wiring is pending; the capability and its tests are in place (M11.2A).
- The health taxonomy is part of the domain contract (`PersistenceHealth` in domain, no Qt, no I/O).
- M11.2B (TESTED, capability only, no production consumer): the Last-Known-Good snapshot lives at `<db>.lkg`; only a HEALTHY primary may refresh it; the SQLite backup API is used (read-only source) so WAL-committed content is captured; the candidate is validated before atomic promotion, and an existing LKG is preserved for all failures occurring before successful atomic promotion (only a validated snapshot is promoted); recovery is STAGED into a caller-supplied destination that is reserved exclusively at creation (`O_CREAT | O_EXCL`, mode `0o600`) — existing/foreign destinations are never overwritten (`FileExistsError`) or deleted, and primary/LKG aliases are rejected (`ValueError`); the primary is never replaced, renamed, or repaired automatically; failed candidates owned by the staging call are removed.
- Automatic startup recovery is NOT implemented; startup preflight is NOT implemented. Startup/recovery orchestration (M11.2D) remains pending and will consume the M11.2B/M11.2C capabilities.
- Repair actions (field repair, quarantine, safe mode) remain unimplemented by design; the taxonomy and the M11.2B capabilities are the contract they will build against.

## Alternatives considered

- **JSON file per settings blob**: human-readable and diffable, but fragile under partial writes and offers no integrity primitives. Rejected in favor of SQLite's transactional integrity and WAL.
- **QSettings (Qt-native)**: zero extra code, but platform-dependent storage locations and no typed health model. Rejected.
- **No persistence port (SQLite used directly in application)**: breaks layering (ADR 0002) and blocks headless testing. Rejected.

## Status

Accepted

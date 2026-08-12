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
- Startup performs read-only health inspection (`inspect_path`) before any write, producing a `PersistenceHealth` classification: MISSING, HEALTHY, CORRUPT_DATABASE, MALFORMED_DATA, LOCKED, ACCESS_FAILURE, IO_FAILURE, UNKNOWN_FAILURE. Inspection never mutates the file.
- Health outcomes drive behavior conservatively: healthy → normal load; anything else → explicit diagnostic, no silent fallback, no destructive repair (repair is a future capability, M11.2B-E).
- Shutdown persistence is best-effort with first-error-wins reporting (see ADR 0002 / lifecycle contract in ARCHITECTURE.md).

## Consequences

- Storage is swappable behind the port; tests use in-memory or temporary-file repositories.
- A corrupt database can never crash startup: every failure mode has a typed diagnostic.
- The health taxonomy is part of the domain contract (`PersistenceHealth` in domain, no Qt, no I/O).
- Recovery actions (backup/restore, repair, safe mode) remain unimplemented by design; the taxonomy is the contract they will implement against.

## Alternatives considered

- **JSON file per settings blob**: human-readable and diffable, but fragile under partial writes and offers no integrity primitives. Rejected in favor of SQLite's transactional integrity and WAL.
- **QSettings (Qt-native)**: zero extra code, but platform-dependent storage locations and no typed health model. Rejected.
- **No persistence port (SQLite used directly in application)**: breaks layering (ADR 0002) and blocks headless testing. Rejected.

## Status

Accepted

# Migration Ledger

Governance authority for evidence-backed Legacy disposition. Every Legacy-derived
statement in governance documents is labeled **LEGACY EVIDENCE** — non-authoritative,
read-only reference. The new contract (this repository's code, ADRs, and governance
docs) supersedes all Legacy content. Zero Legacy files are copied; zero Legacy tests
are executed or adapted.

## Label Policy

1. Any reference to Legacy behavior, claims, or design MUST carry the label
   **LEGACY EVIDENCE** in context.
2. Legacy observations describe the prior codebase; they never justify a new
   requirement on their own. A requirement exists only if the new contract
   (roadmap, ADR, or code) states it.
3. Classification is exact, once per atomic responsibility: ADAPT, REWRITE,
   KEEP (governance responsibility only), or DISCARD. SPLIT is used only with
   separately named child responsibilities.
4. Migration state uses WP states from `docs/STATUS_MATRIX.md` (BACKLOG, READY,
   IN_PROGRESS, REVIEW, VERIFY, BLOCKED, DONE, DEFERRED).

## Practical Ledger (real decisions of the clean rebuild)

**LEGACY EVIDENCE** — audit reference: Legacy commit `63914a00f381104299fa50147220e05c04d5ad7e`. All rows below are non-authoritative; the Python/PySide6 rebuild contract governs.

| ID | Legacy Concept | Legacy Evidence | Decision | Where Implemented / Noted |
| --- | --- | --- | --- | --- |
| ML-101 | Stack: C++20 / Qt 6 with CMake, CTest, Catch2/doctest, `main.cpp` entry point | Legacy roadmap and ADRs prescribed a C++20 architecture | DISCARD (historical superseded plan) | Superseded by ADR 0001: Python 3.11+, PySide6, pytest, Ruff, setuptools. Preserved only as the "historical superseded plan" note in MASTER_ROADMAP_1.0.md |
| ML-102 | Four-layer separation (pure core, UI, I/O, composition root) | Legacy ADR D2/D3/D4 described layer boundaries and state authorities | ADAPT | Re-applied on the Python stack: domain/application/infrastructure/presentation + bootstrap (ADR 0002, ARCHITECTURE.md) |
| ML-103 | Single canonical owner per state category | Legacy ADR D3: five state authorities | ADAPT | ADR 0003: one owning service per state model (PlaybackService→PlaybackState, QueueService→QueueState, LibraryService→LibraryState, SettingsService→SettingsState, NavigationService→NavigationState) |
| ML-104 | QML intent/read-only projection boundary | Legacy ADR D7: QML sends intent, receives read-only projections | ADAPT | ADR 0004: bridges (Playback/Queue/Library/Navigation/Settings) translate intents and expose read-only projections; no Q_PROPERTY/Q_INVOKABLE C++ machinery — PySide6 properties instead |
| ML-105 | Application-owned audio port | Legacy ADR D8: IAudioEngine port, backend deferred | ADAPT | `AudioPort` ABC in `application/ports.py`; `QtMultimediaBackend` (Qt Multimedia, FFmpeg) implements it |
| ML-106 | Persistence ports with Domain unaware of storage | Legacy ADR D9: JSON settings + SQLite app data | ADAPT (storage simplified) | `SettingsRepository` port + `SQLiteSettingsRepository` (WAL). JSON file settings replaced by the SQLite store; library index/queue persistence are Post-1.0 |
| ML-107 | Verified effect pipeline / no fake atomicity | Legacy ADR D10: prepare→execute→verify→publish | ADAPT (principles only) | Error propagation principles in ARCHITECTURE.md: no silent exceptions, first-error-wins shutdown, typed diagnostics. The formal four-phase pipeline machinery is not implemented — principles govern |
| ML-108 | Governance doc set (roadmap, DoD, status matrix, invariants, debt, backlog) | Legacy governance authorities | ADAPT | Retained as the governance skeleton, reconciled to the real stack in this change |
| ML-109 | Video playback, visualizers, video library | Legacy product scope included video features | DISCARD | Product is audio-only; video is Not Applicable (canonical 1.0 contract) and listed in POST_1_0_BACKLOG as N/A |
| ML-110 | Distributed scope: sync, server integrations, home audio, Michi AI, ecosystem features | Legacy roadmap envisioned distributed/ecosystem scope | DISCARD | Local-first, audio-only 1.0; all distributed scope is Post-1.0 (POST_1_0_BACKLOG.md) |
| ML-111 | GStreamer mention in repository metadata | Legacy repo metadata described "PySide6 and GStreamer" | DISCARD (metadata correction) | The rebuild uses Qt Multimedia with FFmpeg backend; metadata descriptions updated opportunistically (TD-014) |
| ML-112 | Legacy tests and fixtures | Legacy test corpus exists in the prior repository | DISCARD (never copied) | New-tests-only policy (INVARIANTS.md): all 154 pytest tests written from scratch |

## Rules

- Rows above are the complete set of Legacy-relevant decisions for the clean rebuild. New Legacy concepts discovered later are admitted here first with a decision before any new-contract effect.
- A classification may change only via an approved scope change recorded in this ledger.
- Migration states: all rows are DONE (decisions recorded and reflected in the new contract) except where a capability remains unimplemented by design (Post-1.0 or Required-1.0-gap entries, tracked in MASTER_ROADMAP_1.0.md and TECHNICAL_DEBT_REGISTER.md).

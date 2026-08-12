# Migration Ledger

Governance authority for evidence-backed disposition of prior material. Two distinct evidence classes exist and MUST NOT be conflated. Every row below states its class explicitly.

## Evidence Classes

### LEGACY EVIDENCE

Authority:

```text
Repository:              pitydah/michi-legacy
Local historical checkout: /home/cristian/music_player
Freeze branch:            feat/m1.3-adapter-restart
Freeze commit:            63914a00f381104299fa50147220e05c04d5ad7e
Freeze tag:               legacy-freeze-2026-08-08
Authority:                READ-ONLY EVIDENCE
```

The historical Legacy application — a Python/PySide6/Qt/QML application with a much larger product scope (AI assistant, audio lab, lyrics, radio, recognition, sync) and historical audio architecture involving GStreamer/MPD backend concepts. It is non-authoritative, read-only reference: no Legacy file is copied, and no Legacy test is executed or adapted.

Note on repository ancestry: the clean rebuild repository (`pitydah/michi-music-player`) has its own empty-root baseline commit `b2c697b53fd0cd9aa172efe47c967d29ec64c9f7`. `b2c697b` is the clean-rebuild root, not a Git continuation or descendant of the Legacy repository, and it does not "orphan" Legacy history. The two repositories are distinct; the freeze commit above is the canonical evidence point for Legacy statements.

### SUPERSEDED CLEAN-REBUILD GOVERNANCE DRAFT

M0 Foundation v2 governance artifacts of **this** rebuild (`openspec/changes/m0-foundation-v2`): roadmap phases M0–M16 and Proposed ADRs D1–D10 (dated 2026-08-10) that anticipated a C++20/Qt 6 architecture with CMake, CTest, and Catch2/doctest, plus debt entries TD-001–TD-007. That anticipated direction was never implemented. These are draft artifacts of the clean rebuild itself — not Legacy code evidence. Superseded by the Accepted ADRs 0001–0006 on the Python/PySide6 stack; they impose **no active requirements**.

## Label Policy

1. Any reference to prior material MUST carry exactly one class label — **LEGACY EVIDENCE** or **SUPERSEDED CLEAN-REBUILD GOVERNANCE DRAFT** — in context.
2. Prior material never justifies a new requirement on its own. A requirement exists only if the active contract (roadmap, Accepted ADR, or code) states it.
3. Classification is exact, once per atomic responsibility: ADAPT, REWRITE, KEEP (governance responsibility only), or DISCARD. SPLIT is used only with separately named child responsibilities. A row whose prior material contains no such concept at all is marked N/A — no concept to classify.
4. Migration state uses WP states from `docs/STATUS_MATRIX.md` (BACKLOG, READY, IN_PROGRESS, REVIEW, VERIFY, BLOCKED, DONE, DEFERRED).

## Ledger — SUPERSEDED CLEAN-REBUILD GOVERNANCE DRAFT

Audit reference: `openspec/changes/m0-foundation-v2` (draft ADRs D1–D10, Proposed, 2026-08-10; roadmap M0–M16 anticipating C++20).

| ID     | Draft Concept                                                                              | Draft Evidence                                                       | Decision                    | Where Implemented / Noted                                                                                                                                                                            |
| ------ | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ML-101 | Stack anticipation: C++20 / Qt 6 with CMake, CTest, Catch2/doctest, `main.cpp` entry point | Draft roadmap and Proposed ADRs anticipated a C++20 architecture     | DISCARD (never implemented) | Superseded by ADR 0001: Python 3.11+, PySide6, pytest, Ruff, setuptools. Preserved only as historical context in MASTER_ROADMAP_1.0.md                                                               |
| ML-102 | Four-layer separation (pure core, UI, I/O, composition root)                               | Draft ADRs D2/D3/D4 described layer boundaries and state authorities | ADAPT                       | Re-applied on the Python stack: domain/application/infrastructure/presentation + bootstrap (ADR 0002, ARCHITECTURE.md)                                                                               |
| ML-103 | Single canonical owner per state category                                                  | Draft ADR D3: five state authorities                                 | ADAPT                       | ADR 0003: one owning service per state model (PlaybackService→PlaybackState, QueueService→QueueState, LibraryService→LibraryState, SettingsService→SettingsState, NavigationService→NavigationState) |
| ML-104 | QML intent/read-only projection boundary                                                   | Draft ADR D7: QML sends intent, receives read-only projections       | ADAPT                       | ADR 0004: bridges (Playback/Queue/Library/Navigation/Settings) translate intents and expose read-only projections; no Q_PROPERTY/Q_INVOKABLE C++ machinery — PySide6 properties instead              |
| ML-105 | Application-owned audio port                                                               | Draft ADR D8: IAudioEngine port, backend deferred                    | ADAPT                       | `AudioPort` ABC in `application/ports.py`; `QtMultimediaBackend` (Qt Multimedia, FFmpeg) implements it                                                                                               |
| ML-106 | Persistence ports with Domain unaware of storage                                           | Draft ADR D9: JSON settings + SQLite app data                        | ADAPT (storage simplified)  | `SettingsRepository` port + `SQLiteSettingsRepository` (WAL). JSON file settings replaced by the SQLite store; library index/queue persistence are Post-1.0                                          |
| ML-107 | Verified effect pipeline / no fake atomicity                                               | Draft ADR D10: prepare→execute→verify→publish                        | ADAPT (principles only)     | Error propagation principles in ARCHITECTURE.md: no silent exceptions, first-error-wins shutdown, typed diagnostics. The formal four-phase pipeline machinery is not implemented — principles govern |
| ML-108 | Governance doc set (roadmap, DoD, status matrix, invariants, debt, backlog)                | Draft governance skeleton                                            | KEEP                        | Retained as the governance skeleton of the clean rebuild, reconciled to the real stack in this change                                                                                                |

## Ledger — LEGACY EVIDENCE

Audit reference: Legacy commit `63914a00f381104299fa50147220e05c04d5ad7e` (Legacy tree at freeze: ~447 QML files, ~1,164 Python test files, no C++ source).

| ID     | Legacy Concept                                                                  | Legacy Evidence                                                                                                                                                        | Decision                                       | Where Implemented / Noted                                                                                                                                                                                                                 |
| ------ | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ML-109 | Video playback, visualizers, video library                                      | Legacy was audio-only: video was explicitly rejected in the Legacy test suite (`tests/qml/workflows_specialized/test_negative_video_rejected.py`)                      | N/A — no Legacy concept to classify            | The clean rebuild independently declares video Not Applicable (canonical 1.0 contract) and lists it in POST_1_0_BACKLOG as N/A. No Legacy video scope exists to discard                                                                   |
| ML-110 | Distributed/ecosystem scope: AI assistant, sync, radio, recognition, home audio | Legacy tree contains `core/ai/`, `core/lyrics/`, `core/home_audio_service.py`, `core/context/providers/snapshot/radio.py`, `recognition.py`, Android sync (`android/`) | DISCARD                                        | Local-first, audio-only 1.0; all distributed/ecosystem scope is Post-1.0 (POST_1_0_BACKLOG.md)                                                                                                                                            |
| ML-111 | GStreamer mention in Legacy repository metadata                                 | The historical Legacy repository description identifies "Python, PySide6 and GStreamer", consistent with Legacy's historical audio architecture                        | N/A — historical evidence, no migration action | No migration action required: this is a historically accurate description of Legacy. The clean rebuild independently uses Qt Multimedia (FFmpeg backend). Stale metadata of the CURRENT clean repository is tracked separately as TD-014. |
| ML-112 | Legacy tests and fixtures                                                       | Legacy test corpus: ~1,164 Python test files in the Legacy tree at freeze                                                                                              | DISCARD (never copied)                         | New-tests-only policy (INVARIANTS.md): all 154 pytest tests written from scratch                                                                                                                                                          |
| ML-113 | Legacy governance documentation                                                 | Legacy tree contains ARCHITECTURE.md, BACKLOG.md, KNOWN_ISSUES.md, and other docs                                                                                      | DISCARD (content); evidence-only               | Current governance derives from the clean-rebuild SDD baseline, not from Legacy docs; Legacy docs are read-only evidence                                                                                                                  |

## Rules

- Rows above are the complete set of prior-material decisions for the clean rebuild. New prior material discovered later is admitted here first, with its evidence class, before any new-contract effect.
- Evidence class assignment MUST be verifiable: LEGACY EVIDENCE rows cite the Legacy tree at freeze; SUPERSEDED CLEAN-REBUILD GOVERNANCE DRAFT rows cite `openspec/changes/m0-foundation-v2`.
- A classification may change only via an approved scope change recorded in this ledger.
- Migration states: all rows are DONE (decisions recorded and reflected in the new contract) except where a capability remains unimplemented by design (Post-1.0 or Required-1.0-gap entries, tracked in MASTER_ROADMAP_1.0.md and TECHNICAL_DEBT_REGISTER.md).

# Master Roadmap 1.0

Michi Music Player — phase plan from empty workspace to Application Navigation.
Each phase adds exactly one verifiable capability. Phases are ordered by hard
dependency; no phase may start before its predecessor exits. Each phase routes
its new-test strategy; without one it may not proceed.

---

## M0 Foundation

**Objective**: Establish the documentation-only foundation — governance authorities,
architecture dimensions, legacy-evidence ledger, and decision-record directory.
No product code, tests, build files, product QML, integrations, or runtime behavior.

**Scope**: 11 paths: `README.md`, `.gitignore`, `docs/MASTER_ROADMAP_1.0.md`,
`docs/ARCHITECTURE.md`, `docs/INVARIANTS.md`, `docs/MIGRATION_LEDGER.md`,
`docs/STATUS_MATRIX.md`, `docs/DEFINITION_OF_DONE.md`,
`docs/TECHNICAL_DEBT_REGISTER.md`, `docs/POST_1_0_BACKLOG.md`, `docs/adr/`.
Stack-neutral `.gitignore` (OS/editor/environment only). Read-only Legacy source
at `63914a00`; zero copies; Legacy tests never executed.

**Out-of-scope**: Playback; audio engine; queue; library; database; playlists;
search; metadata editor; Audio Lab; Disc Lab; Michi AI; sync; NowPlaying;
functional navigation; product QML; server integrations; home audio; recognition;
radio; lyrics; Michi ecosystem features; video. All route to `POST_1_0_BACKLOG`.

**Dependencies**: None — M0 starts from the empty tree
`4b825dc642cb6eb9a060e54bf8d69288fbee4904`.

**Deliverables**: All 11 paths present. README.md links every governance authority.
`.gitignore` contains only OS/editor/environment patterns. Architecture lists
D1–D10 open. `docs/adr/` contains ten Proposed ADRs following the selective
sequence. Migration ledger has 17-field rows with exact classifications. Status
Matrix defines 8 component and 8 WP states. DoD defines DoR, DoD, Golden Path.
Invariants record freeze/reopen, P0/P1 0/0 gate, WIP limits, baby steps,
new-tests-only. Debt register and backlog scaffolded.

**New-test strategy**: N/A — M0 is documentation-only. No code, tests, build
system, or runnable target exists. All assertions are structural shell checks.
Gateway at M1→M2 introduces the first runnable test target.

**Entry criteria**: Empty tree `4b825dc642cb6eb9a060e54bf8d69288fbee4904`.
Approved proposal, spec, design, tasks. No prior product artifacts.

**Exit criteria**: All 11 paths verified. Governance routes remaining phases.
D1–D10 open for autonomous Design. At least one classified ledger row. State
machines validated. DoR, DoD, Golden Path documented. Invariants register freeze,
release gate, new-tests-only. All in-apply checks pass.

**Acceptance gate**: Independent gate inspects all paths. Every D1–D10 says
"open for autonomous Design". Zero product artifacts. `.gitignore` rejects
stack tokens. Hybrid parity passes. Gate recorded in state.yaml.

**Risks**: Terminology drift between authorities; Legacy implying inherited
design. Mitigated by exact names, canonical ownership, classification rules.

---

## M1 Bootstrap

**Objective**: Build system, project scaffold, and empty application shell that
compiles, links, and starts without crashing. No playback, no UI content.

**Scope**: CMake build (C++20, Qt 6 Widgets/Quick minimum linkage). Empty
`main.cpp` with lifecycle stubs. Compile-time layer graph validated:
Presentation→Application, Infrastructure→Application ports, Application→Domain,
Domain→no outward dependencies.

**Out-of-scope**: Audio output; playback controls; QML screens beyond empty
window; queue; library; database; search; navigation.

**Dependencies**: M0 Foundation — D1–D10 and ADRs must be Proposed before M1
selects tooling.

**Deliverables**: `CMakeLists.txt`, empty `main.cpp`, four-layer directory
scaffold, CI config (build-only). Successful compile and link.

**New-test strategy**: Unit (layer compilation), Integration (shell start/exit).
Framework: CTest + Catch2/doctest. Command: `cmake --build build && ctest
--test-dir build`. Coverage: build verification only.

**Entry criteria**: M0 DONE. All M0 paths verified. D1–D10 open. ADR sequence
D1–D8 at minimum Proposed.

**Exit criteria**: Shell compiles, links, starts, shuts down cleanly under
CTest. Layer compile graph validated (no reverse dependency). CI build passes.

**Acceptance gate**: `cmake --build build` exits 0. Binary starts and exits 0
within 30 s. No runtime audio dependency linked. CTest build-verification passes.

**Risks**: Premature tooling before D1–D8 Proposed. Mitigated by entry gate.

---

## M2 Minimal Playback

**Objective**: Play a single audio file from start to finish. Prove the audio
pipeline end-to-end with start/stop only.

**Scope**: AudioEnginePort in Application. Infrastructure audio adapter. Single
hardcoded file path. Start/stop commands. Error handling (file not found,
unsupported format).

**Out-of-scope**: Multiple files; playlist; queue; seek; pause/resume; repeat;
shuffle; UI beyond start/stop button; library browsing.

**Dependencies**: M1 Bootstrap — shell must compile, link, and start.

**Deliverables**: `AudioEnginePort` interface, infrastructure adapter,
start/stop handlers, error handling. `M2_MINIMAL_PLAYBACK_TEST` CTest target.

**New-test strategy**: Unit (port contract, error paths), Integration (pipeline
with known WAV). Command: `ctest -R M2_MINIMAL_PLAYBACK`. Test fixture: synthetic
440 Hz sine WAV.

**Entry criteria**: M1 DONE. Shell exits 0. AudioEnginePort design finalized in
ADR. Test fixture audio file prepared.

**Exit criteria**: Known WAV plays start to end. Lifecycle transitions verified.
File-not-found and unsupported-format produce explicit diagnostics (no crash).
M2 CTest target passes.

**Acceptance gate**: Automated test plays synthetic audio, validates output
buffer non-silent. Error cases deterministic. No controls beyond start/stop.
No queue or library code.

**Risks**: Platform-specific backend coupling constraining portability.
Mitigated: Infrastructure adapter hides backend behind AudioEnginePort.

---

## M3 Complete Playback

**Objective**: Full playback state machine — play, pause, resume, stop, seek,
previous, next. Every control transitions through documented states.

**Scope**: Playback state machine (Stopped→Playing→Paused→Playing/Stopped).
Seek within bounds. Previous/next in flat list. Volume control. Position
reporting. Track metadata (title, artist, album, duration).

**Out-of-scope**: Queue management; shuffle; repeat; library scanning; database;
playlist files; crossfade; gapless; audio effects.

**Dependencies**: M2 Minimal Playback — audio pipeline must work for a single file.

**Deliverables**: PlaybackState enum with transition guard. SeekController.
VolumeController. Flat track list navigation. Position/duration reporting.
Metadata extraction (MP3, FLAC, WAV). `M3_COMPLETE_PLAYBACK_TEST` CTest target.

**New-test strategy**: Unit (state machine, seek bounds, volume range, metadata),
Integration (e2e playback sequence). Command: `ctest -R M3_COMPLETE_PLAYBACK`.

**Entry criteria**: M2 DONE. Single-file playback passes. Port stable. At least
two synthetic test tracks available.

**Exit criteria**: Every documented transition produces correct output. Seek to
0, mid, end validated. Previous loops to last; next to first. Volume 0 silent;
max unclipped. Metadata parsed for MP3, FLAC, WAV. All M3 tests pass.

**Acceptance gate**: Automated sequence play→pause→resume→seek→next→previous→stop.
Each transition verified. Metadata matches known tags. Position within ±100 ms.

**Risks**: Seek precision varies by codec; metadata encoding inconsistencies.
Mitigated: per-format tolerances; parser handles UTF-8, Latin-1, fallback.

---

## M4 Queue

**Objective**: Queue state authority — add, remove, reorder, shuffle, repeat
(none/one/all). Queue owns playback order; playback engine consumes from Queue.

**Scope**: Queue add/remove/move/clear. Shuffle (deterministic seed). Repeat
modes. Queue→Playback feed obeys order, shuffle, repeat. Queue survives
playback lifecycle.

**Out-of-scope**: Persistence across restart (M5); drag-and-drop UI; save/load
queue files; library integration (flat list only).

**Dependencies**: M3 Complete Playback — controls must work before Queue feeds them.

**Deliverables**: `Queue` domain model. QueueController. ShuffleEngine
(deterministic). RepeatPolicy. Queue→Playback integration. `M4_QUEUE_TEST`.

**New-test strategy**: Unit (operations, shuffle determinism, repeat, edge cases:
empty, single, duplicates), Integration (Queue→Playback feed). Command:
`ctest -R M4_QUEUE`.

**Entry criteria**: M3 DONE. Playback state machine validated. Flat list
navigation works.

**Exit criteria**: Add/remove/move/clear produce correct state. Shuffle
reproducible per seed. Repeat modes correct. Empty queue produces deterministic
diagnostic. All M4 tests pass.

**Acceptance gate**: Populate→shuffle→play through→verify every track played
expected times per repeat mode. Remove/add/clear mid-playback produce correct
next-track behavior.

**Risks**: Shuffle randomness causing flaky tests. Mitigated: deterministic seed.
Queue unbounded growth — mitigated: explicit max-size invariant.

---

## M5 Database

**Objective**: Persistence via Settings, Cache, and UserData ports. Durable schema.
Restart recovery preserves Queue, position, volume, preferences.

**Scope**: SettingsPort, CachePort, UserDataPort. Infrastructure SQLite adapter
(versioned schema, migration-capable). Persist: volume, last track/position,
queue, repeat, shuffle seed, window geometry, theme. Startup recovery: restore
or fresh start on failure.

**Out-of-scope**: Library database (M6); playlist files; cloud sync; profiles;
encryption.

**Dependencies**: M4 Queue — state must be defined before persistence.
M3 Playback — position/volume must be defined.

**Deliverables**: Three port interfaces. SQLite adapter. Migration framework
(v1→vN). Startup recovery flow. `M5_DATABASE_TEST` CTest target.

**New-test strategy**: Unit (port contracts, schema, migration idempotency),
Integration (write→restart→read, corruption recovery). Command:
`ctest -R M5_DATABASE`.

**Entry criteria**: M4 DONE. Queue operations validated. Position and volume
accessible via public interfaces.

**Exit criteria**: Write→kill→restart→read preserves all fields within tolerance.
Corrupted DB triggers explicit recovery — never crashes. Migration vN→vN+1
idempotent. All M5 tests pass.

**Acceptance gate**: Persistence cycle: set volume/position/queue/repeat→kill→
restart→verify. Corruption test: garbage DB→restart→clean recovery with
user-visible diagnostic.

**Risks**: Migration failures causing data loss. Mitigated: transactional
migration; rollback preserves previous schema. File locking on concurrent
access — mitigated: single-process architecture.

---

## M6 Library

**Objective**: Library state authority — scan directories, index audio files,
extract metadata, browsable collection. Library feeds Queue; Queue feeds Playback.

**Scope**: LibraryScanner (recursive, file-type filter). Metadata index (artist,
album, title, duration, format, path). Browse by artist, album, track.
Incremental scan (add/remove/update). Library→Queue integration.

**Out-of-scope**: Internet metadata; cover art; tag editing; duplicate detection;
waveform; playlist files.

**Dependencies**: M5 Database — library index persisted through database ports.

**Deliverables**: `Library` domain model. LibraryScanner with include/exclude.
MetadataIndex. Incremental scan. Library→Queue feed. `M6_LIBRARY_TEST`.

**New-test strategy**: Unit (scanner filtering, metadata, incremental diff),
Integration (scan→index→browse→enqueue), Performance (10k files <5 s).
Command: `ctest -R M6_LIBRARY`.

**Entry criteria**: M5 DONE. Database ports operational. Schema supports library
index tables.

**Exit criteria**: Scanner indexes all supported audio files. Incremental scan
handles add/remove/update. Browse returns correct hierarchy. Library→Queue
works. 10k-file scan under 5 s. All M6 tests pass.

**Acceptance gate**: Scan fixture (N artists, M albums, T tracks). Browse
verifies hierarchy. Delete file→rescan→removed. Add file→rescan→appears.
Performance threshold measured and recorded.

**Risks**: Large libraries freezing UI. Mitigated: worker-thread scanner with
progress callbacks. Metadata encoding edge cases — mitigated: hardened parser
from M3 with expanded test corpus.

---

## M7 Search

**Objective**: Full-text search across Library index — artist, album, title.
Results are actionable: play, add to queue.

**Scope**: SearchEngine with tokenized, case-insensitive, diacritic-insensitive
matching. Scope: artist, album, title, filename. Combined queries (AND).
Relevance-ranked results. Actionable: play now, add to queue.

**Out-of-scope**: Natural-language queries; fuzzy matching; acoustic search;
internet search; search history; lyrics search.

**Dependencies**: M6 Library — index must be populated before search operates.

**Deliverables**: `SearchEngine` with tokenizer and ranker. SearchController.
Search→Playback and Search→Queue integration. `M7_SEARCH_TEST` CTest target.

**New-test strategy**: Unit (tokenizer, case/diacritic folding, ranking, empty
query), Integration (search→play, search→enqueue). Command:
`ctest -R M7_SEARCH`.

**Entry criteria**: M6 DONE. Library populated, browsable. ≥100 indexed tracks
with varied diacritics and mixed case.

**Exit criteria**: Single-token returns all matches. Multi-token (AND) returns
intersection. Case/diacritic-insensitive. Empty query no crash. "Play now"
starts playback. "Add to queue" enqueues. All M7 tests pass.

**Acceptance gate**: Known-fixture queries return expected counts and rankings.
Diacritic folding validated (NFC normalization at index and query time).
Actionable results trigger correct commands. Search across 10k tracks <200 ms.

**Risks**: Performance degrading with library size. Mitigated: FTS5 indexed
search; benchmarks at 10k/50k/100k tracks.

---

## M8 Application Navigation

**Objective**: Wire all capabilities into a navigable shell. Screen transitions,
state preservation, and the complete Golden Path.

**Scope**: App shell with NowPlaying, Queue, Library, Search, Settings screens.
Navigation bar. Screen state preservation. Deep links: search→NowPlaying,
library→Queue. Complete Golden Path executable and verifiable.

**Out-of-scope**: Theming; animations; accessibility; localization; onboarding
wizard; Settings beyond volume/library-path; Michi AI; Audio Lab; Disc Lab.

**Dependencies**: M7 Search, M6 Library, M5 Database, M4 Queue — all upstream
capabilities must exit before navigation wires them.

**Deliverables**: App shell with navigation. Five screen components. State
preservation. End-to-end Golden Path test script. `M8_NAVIGATION_TEST`.

**New-test strategy**: E2E (complete Golden Path), Integration (screen state
preservation), Acceptance (executable Golden Path script). Framework: CTest
with app test harness. Command: `ctest -R M8_NAVIGATION`.

**Entry criteria**: M4–M7 all DONE. Golden Path partially validated at each
upstream boundary.

**Exit criteria**: Every screen accessible. State survives transitions. Deep
links route correctly. Golden Path runs end-to-end without manual intervention.
Restart restores prior session. All M8 tests pass.

**Acceptance gate**: Automated Golden Path: launch→Library→scan→browse→
select track→play→verify position→pause→resume→seek→next→add album to
Queue→shuffle→verify order→Search→search→play result→close→restart→verify
Queue, position, volume restored. Every step has pass/fail assertion.

**Risks**: Screen transitions causing state loss. Mitigated: state hoisted to
Application; Presentation screens stateless. Navigation stack unbounded —
mitigated: depth limit and back-stack pruning.

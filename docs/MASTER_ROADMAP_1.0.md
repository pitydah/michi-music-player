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

---

## M9 UI Foundation

**Objective**: Establish a reusable QML UI foundation with semantic design tokens,
reusable primitives, interaction states, keyboard accessibility, and
regression-protected application shell styling.

**Scope**: Semantic dark theme tokens (palette, spacing, radii, typography,
control sizes, motion). Reusable primitives: MichiButton (primary/secondary/ghost,
hover/pressed/disabled/checked/focus), MichiTextField, MichiPanel, MichiSlider.
Interaction states on all new components. Keyboard-accessible Sidebar with
ItemDelegate. Library/Queue row hover. QML smoke tests with QQmlComponent
verification. Routed-layout regression guards.

**Out-of-scope**: Light theme; custom user accent selection; font scaling
settings; full screen-reader audit; WCAG AA compliance audit; i18n framework;
language packs; onboarding wizard; advanced page animations; reduced-motion
preference; artwork pipeline.

**Dependencies**: M8 Application Navigation — shell structure exists. M1-M7
core — playback/library/queue functional.

**Deliverables**: MichiTheme.qml (singleton), MichiButton, MichiTextField,
MichiPanel, MichiSlider. Themed Sidebar, ContentHost. Migrated NowPlayingView,
LibraryView, QueueView, PlaybackControls, VolumeControl, NowPlayingPanel,
QueuePanel. QML smoke tests. Routed root geometry regression guards.

**New-test strategy**: QQmlComponent smoke tests for theme and all primitives.
Structural regression guards preventing anchors.fill on StackLayout-managed roots.
Headless CI execution via QT_QPA_PLATFORM=offscreen.

**Entry criteria**: M8 DONE. All three routes functional.

**Exit criteria**: All primitives instantiate via QQmlComponent. Routed views
render without geometry conflicts. Keyboard navigation functional in Sidebar.
Hover states on interactive rows. Zero QML warnings. Full automated suite passes.

**Acceptance gate**: QML smoke suite + routed regression guards + pytest + ruff
+ build all green. GitHub Actions CI green.

**Risks**: Theme token drift as features evolve — mitigated by single source of
truth in MichiTheme.qml. Layout regression from anchors.fill reintroduction —
mitigated by automated regression guard.

**Deferred capabilities**: Light theme, custom accents, font scaling, WCAG AA,
i18n, onboarding, animations, reduced-motion → future UI enhancement phase.

---

## M10 Settings & Durable Preferences

**Objective**: Introduce explicit Application ownership for persisted
preferences, integrate only preferences backed by existing runtime capabilities.

**Internal slices**: M10.1 Settings Ownership, M10.2 Existing Preference
Integration, M10.3 Settings Navigation + Bridge, M10.4 Minimal Settings UI,
M10.5 Restart / Persistence Gate.

### M10.1 — Settings Ownership

**Scope**: SettingsService as sole persisted preference owner. SettingsRepository
port (no SQLite in Application). Public API: set_playback_preferences(),
set_last_directory(), set_recent_files(). Deterministic save(). Full-state
preservation on partial update. Bootstrap uses public API only, never mutates
SettingsState directly.

**Deliverables**: src/michi/application/settings_service.py. Lifecycle regression
test proving volume/muted update preserves last_directory and recent_files.
Bootstrap integration.

**Entry criteria**: M5 Database/Settings operational. PlaybackService snapshot API.

**Exit criteria**: SettingsService is sole SettingsState mutation authority.
Bootstrap mutates nothing directly. Full-state preservation test passes.

### M10.2 — Existing Preference Integration (FUTURE)

**Scope**: last_directory integration. Successful Library scan persists
last_directory. Startup loads persisted path as default directory. NO auto-scan.

### M10.3 — Settings Navigation + Bridge (FUTURE)

**Scope**: SETTINGS AppRoute, SettingsBridge, Navigation integration.

### M10.4 — Minimal Settings UI (FUTURE)

**Scope**: UI for playback preferences (volume, muted) and library (last_directory).

### M10.5 — Restart / Persistence Gate (FUTURE)

**Scope**: End-to-end: set preference → save → restart → restore → assert.

**Out-of-scope (deferred)**: Output device selector, replay gain, crossfade,
gapless, default repeat, shuffle seed, theme selection, language, font size,
JSON import/export. All require existing capability owners first.

**Principle**: Settings exposes existing capabilities. Settings does not create
missing product capabilities.

**Dependencies**: M5 Database (SettingsRepository, SQLite). M9 UI Foundation
(for M10.4). PlaybackService snapshot_volume API.

**Risks**: SettingsState partial overwrite — mitigated by set_playback_preferences
public API + full-state preservation tests. Scope creep into nonexistent features
— mitigated by explicit deferred list and capability-owner gate.

---

## M11 Resilience

**Objective**: The application handles failure gracefully — crash recovery,
corruption recovery, and degraded-mode operation without data loss.

**Scope**: Crash recovery: last-known-good state restoration. Database
corruption detection and repair. Graceful degradation: missing codec shows
diagnostic, not crash. Watchdog timer for audio pipeline stall. Error
telemetry (opt-in, anonymous, privacy-preserving). Safe-mode launch
(--safe-mode flag bypasses audio, cache, extensions).

**Out-of-scope**: Automatic bug reporting; remote crash analytics; hardware
failure recovery; filesystem-level recovery; network resilience (no network
features yet).

**Dependencies**: M5 Database — corruption detection builds on migration
framework. M10 Settings — safe-mode disables cached settings. M3 Complete
Playback — pipeline stall detector requires playback state machine.

**Deliverables**: Crash recovery manager. DB integrity checker with
auto-repair. Safe-mode launcher. Watchdog with configurable timeout. Error
telemetry channel (opt-in). Degraded-mode state machine.
`M11_RESILIENCE_TEST`.

**New-test strategy**: Unit (corruption detection, safe-mode flag parser,
telemetry opt-in gate), Integration (inject crash signal, verify recovery;
corrupt DB pages, verify repair; inject pipeline stall, verify watchdog),
Acceptance (chaos test: random kill during playback, verify full recovery
with no data loss). Command: `ctest -R M11_RESILIENCE`.

**Entry criteria**: M10 DONE. Settings persistence verified. DB migration
framework operational. Playback state machine stable. Fuzzed-corpus of
corrupt SQLite pages prepared.

**Exit criteria**: Kill during playback→restart restores queue, position,
volume, settings within tolerance. Corrupt DB→explicit repair message→
recover or fresh start. Safe-mode launches without audio/cache. Watchdog
detects pipeline stall within 5 s and restarts pipeline. Telemetry disabled
by default; opt-in persisted. All M11 tests pass.

**Acceptance gate**: Chaos sequence: populate library→play→kill -9→restart→
verify state→corrupt DB→restart→verify repair→safe-mode launch→verify
audio bypassed→normal launch→verify full function. Zero silent data loss.
Every error path produces user-visible diagnostic.

**Risks**: Recovery logic itself introducing data loss. Mitigated: recovery
never mutates until integrity confirmed; write-ahead log preserved. Watchdog
false positives — mitigated: configurable timeout; progressive escalation.

---

## M12 Performance

**Objective**: Quantify and optimize — the application meets performance budgets
on target hardware before entering Beta.

**Scope**: Frame-time budget (≤16 ms per frame, 60 FPS target). Library scan:
10k files <5 s. Search: 100k index <200 ms. Queue operations: <1 ms for 10k
tracks. Startup: to-NowPlaying <2 s cold, <500 ms warm. Memory: <256 MB RSS
with 100k library. Benchmark harness (micro + macro). CI performance gate
(regression ≥10% fails build).

**Out-of-scope**: GPU profiling; power/thermal optimization; embedded-hardware
tuning; network-latency optimization; disk-I/O beyond SQLite pragmas.

**Dependencies**: M8 Application Navigation — Golden Path must be stable to
profile. M6 Library — scan/search benchmarks require library. M7 Search —
search benchmarks require index. M11 Resilience — watchdog must not fire
during normal profiles.

**Deliverables**: Benchmark harness (micro: per-component; macro: Golden Path).
Frame profiler integration. Performance test suite. CI regression gate.
Optimization report with before/after per phase. `M12_PERFORMANCE_TEST`.

**New-test strategy**: Benchmark (micro: scan, search, queue operations, startup;
macro: Golden Path timing), Regression (CI gate at ±10%), Profiling
(frame-time trace captured and compared to budget). Command:
`ctest -R M12_PERFORMANCE`.

**Entry criteria**: M11 DONE. Crash recovery and safe-mode verified. Golden
Path stable end-to-end. Benchmark fixture: 10k-file synthetic library with
varied metadata. CI hardware spec documented.

**Exit criteria**: 60 FPS maintained during playback with library visible.
Scan 10k files <5 s. Search 100k index <200 ms. Queue ops <1 ms for 10k.
Startup cold <2 s, warm <500 ms. Memory <256 MB RSS at 100k library. CI
gate rejects ≥10% regression. All M12 benchmarks pass.

**Acceptance gate**: Benchmark run on reference hardware: every budget met.
Three consecutive CI runs within gate. Profiling report filed with frame
budget, memory, startup. Golden Path macro-benchmark completes within budget.

**Risks**: CI hardware variance masking regressions. Mitigated: relative-to-
baseline comparison per run; tolerance band. Optimization chasing diminishing
returns — mitigated: budgets are ceilings, not targets.

---

## M13 Packaging

**Objective**: Installable, distributable, signed artifacts for every target
platform — users can install via native package manager or direct download.

**Scope**: Linux: AppImage, Flatpak, deb (Ubuntu 22.04+). Windows: MSIX, portable
zip. macOS: signed .dmg bundle. Auto-update channel (AppImage/Flatpak native,
Sparkle on macOS). Icon asset suite (16×16 through 512×512, .ico, .icns, .svg).
Desktop integration (MIME registration, file-association .mp3/.flac/.wav/.ogg).
CLI entry point (`michi --play <file>`, `--version`, `--safe-mode`).

**Out-of-scope**: Store submission (App Store, Play Store, Snap Store);
enterprise deployment (MSI, GPO); container images; embedded build; portable
build for non-desktop targets.

**Dependencies**: M12 Performance — packaging requires release-mode build with
optimizations enabled. M10 Settings — CLI flags must interact with persisted
settings correctly.

**Deliverables**: CMake packaging targets for all platforms. CI packaging
pipeline. Icon suite. Desktop integration files. CLI entry point. Auto-update
descriptor. `M13_PACKAGING_TEST` (install, launch, update, uninstall smoke).

**New-test strategy**: Integration (install→launch→verify version→uninstall
clean), Smoke (each package type on target OS; file-association opens app),
CLI (every flag produces correct behavior). Command:
`ctest -R M13_PACKAGING`.

**Entry criteria**: M12 DONE. Performance budgets met. Release-mode build
passes on all platforms. Code signing certificates provisioned. Icon assets
from design spec rendered at all resolutions.

**Exit criteria**: Each package type installs and launches on target OS.
File-association opens audio file in Michi. CLI `--version` reports correct
semver. `--safe-mode` bypasses audio/cache. Uninstall removes binary and
leaves user data (opt-in clean). Auto-update channel validates against
signed manifest. All M13 tests pass.

**Acceptance gate**: Per-platform: install→launch→open .mp3 from file manager→
play→close→update (via channel)→verify version bump→uninstall. CLI flags
exercise every documented option. Desktop file validates against
freedesktop.org spec.

**Risks**: Code-signing revocation or expiry blocking installs. Mitigated:
timestamped signatures; offline fallback. Flatpak sandbox restricting
filesystem access — mitigated: portal API for directory access.

---

## M14 Beta

**Objective**: Public beta release with telemetry, feedback loop, and
issue triage — real-world validation before RC.

**Scope**: Beta opt-in channel with signed updates. Anonymous telemetry
(opt-in: feature usage, crash count, performance histograms; zero PII).
In-app feedback form. Public issue tracker triage process. Beta onboarding
flow (what's new, known issues, feedback instructions). Staged rollout
(10%→50%→100% of beta channel).

**Out-of-scope**: Marketing website; press kit; social media campaign; paid
user acquisition; NPS survey; focus groups.

**Dependencies**: M13 Packaging — beta users must install via packages.
M11 Resilience — crash telemetry requires recovery infrastructure. M12
Performance — performance telemetry requires benchmark baseline.

**Deliverables**: Beta channel in auto-update. Telemetry pipeline (collect,
aggregate, dashboard). In-app feedback form with screenshot attachment.
Issue triage SLA (P0 ≤24 h, P1 ≤72 h, P2 ≤1 week). Beta release notes.
Staged rollout toggle. `M14_BETA_TEST`.

**New-test strategy**: Integration (telemetry collector verifies anonymization,
feedback submission round-trip), E2E (beta install→opt-in telemetry→use
app→verify dashboard shows data), Acceptance (staged rollout gates).
Command: `ctest -R M14_BETA`.

**Entry criteria**: M13 DONE. All packages signed and installable. Telemetry
server provisioned. Issue tracker configured with beta label. Beta EULA
and privacy notice approved.

**Exit criteria**: Beta channel delivers signed updates. Telemetry dashboard
shows feature-usage and crash-count (zero PII). Feedback form submits with
screenshot. Staged rollout gates honor percentages. P0 triage SLA met in
≥95% of cases over trial period. All M14 tests pass.

**Acceptance gate**: End-to-end beta flow: install→opt-in telemetry→play 10
tracks→crash simulation→restart→crash telemetry transmitted→feedback form
submit→dashboard shows session→update to next beta→verify version bump.
Anonymization verified: no user-identifiable data in telemetry payload.

**Risks**: Telemetry data breach exposing user behavior. Mitigated: client-side
aggregation; zero raw paths or filenames transmitted; periodic privacy audit.
Beta quality damaging reputation — mitigated: staged rollout; instant
rollback capability.

---

## M15 Release Candidate

**Objective**: Final stabilization — zero known P0/P1, complete docs, migration
from Legacy verified, RC artifacts signed and frozen.

**Scope**: Bug triage: all P0/P1 resolved with verified fix. Regression test
suite covering Golden Path, resilience, packaging. Documentation complete:
user manual, FAQ, migration guide from Legacy. Legacy→Michi migration tool
(import Legacy library paths, settings if compatible). RC builds signed
across all platforms. Release notes final. License and attribution complete.

**Out-of-scope**: New features; UI redesign; architecture changes; third-party
integration beyond Legacy migration; feature requests.

**Dependencies**: M14 Beta — all beta feedback triaged. M13 Packaging — RC
builds from same pipeline. M11 Resilience — recovery from every reported
crash path verified.

**Deliverables**: P0/P1 register (empty). Regression suite ≥95% pass rate
on all platforms. User manual. FAQ. Migration guide. Legacy migration tool.
RC signed artifacts. Final release notes. `M15_RC_TEST`.

**New-test strategy**: Regression (full test suite across platforms, ≥95%
pass), Migration (Legacy→Michi import round-trip for settings and library),
Acceptance (RC smoke on each platform: install, Golden Path, uninstall).
Command: `ctest -R M15_RC`.

**Entry criteria**: M14 DONE. Beta telemetry stable. All beta P0/P1 triaged
with disposition (fix/wontfix/duplicate). No known P0. No known data-loss
P1. Documentation drafts in review.

**Exit criteria**: P0 register empty. P1 register empty (all fixed or
classified P2 with documented workaround). Regression suite ≥95% pass.
User manual, FAQ, migration guide published. Legacy migration tool imports
library paths and compatible settings without data loss. RC artifacts signed
on all platforms. Release notes approved. All M15 tests pass.

**Acceptance gate**: Zero P0. Zero P1. Full regression pass on Linux,
Windows, macOS (≥95%). Legacy migration: import library→verify tracks
playable→verify metadata preserved→verify settings migrated (compatible
subset). RC installs, updates, and uninstalls cleanly on all platforms.

**Risks**: Late-discovered P0 from RC testing. Mitigated: RC period minimum
2 weeks; no code changes except P0 fixes. Legacy migration edge cases —
mitigated: dry-run mode with diff report before destructive import.

---

## M16 Michi Music Player 1.0 Stable

**Objective**: Public stable release — 1.0 ships to all users. Golden Path
verified, packages published, project declared FROZEN.

**Scope**: Stable channel published (all platforms). Auto-update from RC→Stable
and Beta→Stable. Version bump to 1.0.0. Public release announcement. Website
update with download links. Project state transition to FROZEN per
INVARIANTS.md freeze gate (stable contract, tests passed, integration
verified, architecture verification, P0=0, P1=0). Post-1.0 planning:
backlog grooming and 1.1 roadmap draft.

**Out-of-scope**: 1.1 development; new features; post-release hotfix process
(defined but not exercised); marketing beyond announcement; paid support.

**Dependencies**: M15 Release Candidate — RC must exit with zero P0/P1.
All preceding M1–M14 capabilities must be DONE. Hybrid parity verified
(OpenSpec + Engram mirrors stable artifacts). Invariants freeze gate
satisfied (P0=0, P1=0, stable contract, tests passed, integration verified,
architecture verified).

**Deliverables**: Stable release packages (all platforms). Signed auto-update
manifests. Release announcement (changelog, download links, migration
instructions). Project FROZEN state declaration. Post-1.0 backlog
prioritization. `M16_STABLE_TEST`.

**New-test strategy**: Acceptance (stable install→Golden Path→update from
RC/Beta→uninstall), Smoke (per-platform, per-package-type), Integrity
(checksum verification, signature validation on all artifacts). Command:
`ctest -R M16_STABLE`.

**Entry criteria**: M15 DONE. P0=0, P1=0. RC artifacts signed and approved.
Website ready for stable release. Release announcement drafted and approved.
Freeze prerequisites (INVARIANTS.md) all satisfied.

**Exit criteria**: Stable packages signed and published on all platforms.
Auto-update delivers stable from RC and Beta channels. 1.0.0 version
reported correctly. Golden Path executes on clean install for all platforms.
Release announcement published. Project state FROZEN recorded. Post-1.0
backlog populated with 1.1 candidates. All M16 tests pass.

**Acceptance gate**: Gold master: download stable→install→Golden Path full
sequence→verify 1.0.0→update check confirms latest→uninstall→reinstall→
restore from backup→verify all data. RC→Stable update path. Beta→Stable
update path. Checksums and signatures validate on all artifacts. Release
announcement links all resolve. Project FROZEN gate: P0=0, P1=0,
architecture verified, integration verified, stable contract.

**Risks**: Last-minute packaging issue on one platform delaying all. Mitigated:
per-platform independent publishing; partial launch acceptable with
documented timeline. Website outage during launch — mitigated: CDN-hosted
downloads with direct-link fallback.

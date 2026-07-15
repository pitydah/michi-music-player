# QML Functional Elements Migration

Date: 2026-07-15

Baseline: `3be3cea69d5368530477ba45a95b7f6b3aca77e6`

Working branch: `codex/qml-functional-elements-migration`

## Purpose

Move functional ownership out of QtWidgets/legacy modules and make the default
QML application use the productive composition root. This migration does not
claim physical audio parity or stable-release readiness.

## Analysis of the previous candidate

`qml-real-functions-x10-v3` was audited but not merged. Its useful core-service
extraction was retained selectively. The branch itself was rejected because:

- its GitHub Actions YAML did not parse;
- its V13 runtime crashed while inspecting the service container;
- 9 of its 15 new workflow tests failed;
- its report claimed 100% while physical features remained deferred;
- it deleted broad widget/test surfaces before establishing a green gate.

## Migrated elements

| Element | Previous state | Current state |
| --- | --- | --- |
| QML launcher | Loaded `Main.qml` without services or bridges | Uses `ApplicationBootstrap`, registers context, loads QML, shuts down services |
| Playlist import/export | `core` imported `legacy_widgets.ui.playlist_io` | Parser and atomic M3U export owned by `core.playlist_io` |
| Connection profiles | Placeholder service | Core facade owns manual profiles, discovery state, diagnostics and capability errors |
| Home Audio groups | Placeholder service and mixed controller names | Core facade owns group lifecycle and exposes the bridge contract |
| Service composition | Nine `object()` placeholders | Concrete or explicitly unavailable services; zero `object()` registrations |
| Route validation | Counted every `navigate()` call as success | Asserts resulting route and records capability-blocked routes separately |
| Capability routing | Navigation never received factory capabilities | Factory derives capabilities from registered services and updates navigation |
| QML package | Wheel contained zero QML files | Wheel contains all 380 QML files and `Main.qml` |
| Legacy package surface | Wheel shipped `ui/window.py` | Main wheel excludes `ui` and `legacy_widgets`; legacy source remains in repository |
| Job workflow tests | Used removed `JobStatus`/legacy API | Uses durable `JobState`, `create_job`, `cancel_job` and persistence cleanup |

## Runtime status

| Domain | Status | Notes |
| --- | --- | --- |
| Library, playback, queue, playlists, history, radio, mix | MIGRATED | Productive routes navigate successfully |
| Connections | MIGRATED_WITH_BOUNDARY | Profile/discovery facade is real; live Michi Link requires a configured client |
| Home Audio | MIGRATED_WITH_BOUNDARY | Group lifecycle is real; HA/Snapcast network actions require configured adapters |
| Accessibility | MIGRATED | Visual settings work without playback; mono/balance require playback capability |
| Michi AI | CAPABILITY_GATED | `core.michi_ai_service` is absent; route is blocked honestly |
| Physical audio, MTP, real receivers, optical disc | PENDING_PHYSICAL | No claim until hardware validation passes |
| Full historical QML regression suite | AUDIT_DEBT | Collection is clean; known accessibility/page-contract failures remain |

## Verification

- `ruff check .`: passed.
- Python `compileall`: passed.
- QML compile-all: 380/380, zero errors and zero warnings.
- Productive QML runtime: passed; 12 routes navigated and AI capability-blocked.
- QML collection: 8,920 tests, zero collection errors.
- Productive workflows V12: 135 passed.
- Connections workflow: 25 passed.
- Durable audio jobs workflow: 10 passed.
- Functional migration contracts: 4 passed.
- Focused playlist/Home Audio/connections/jobs set: 42 passed.
- Wheel inspection: 380 QML resources, `Main.qml` present, no `ui/window.py`, no `legacy_widgets`.
- Clean wheel install: the installed `michi` launcher loaded QML and returned exit code 0.

## Remaining release work

1. Integrate or implement `MichiAIServiceV2` without copying the divergent AI branch.
2. Reduce the full QML regression audit to zero failures, starting with page accessibility contracts.
3. Run the 21/21 physical audio matrix with real devices.
4. Remove or archive the remaining local QtWidgets source only after replacement workflows pass.

## Rollback

The migration is isolated on its working branch. Before merge, rollback is
simply switching back to `main`; no database migration or destructive schema
change is included.

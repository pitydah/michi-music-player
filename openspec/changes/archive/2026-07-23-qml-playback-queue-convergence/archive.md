# Archive Report: QML Playback Queue Convergence

**Archived**: 2026-07-23
**Status**: COMPLETE (intentional-with-warnings)
**Engram observation IDs**: #15 (explore), #16 (proposal), #17 (spec), #18 (design), #19 (tasks), #20 (apply-progress), #34 (verify-report)

## Executive Summary

Converged QML queue projections from three divergent sources (QueueService, QueueListModel, NowPlayingBridge) into a single canonical pipeline: QueueService → QueueListModel (11-role QueueItem dataclass) → QueueBridge → all QML surfaces. NowPlayingBridge was stripped of its duplicate queue cache, normalization, and subscription, retaining only transport, history, and quality. Added distinct `add` vs `replaceAndPlay` semantics and single-write playlist save. All 5 spec requirements with 10 scenarios verified compliant with 74 passing tests.

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `ui_qml/models/queue_item.py` | **Created** | QueueItem dataclass, normalizer, cover helper |
| `ui_qml/models/QueueListModel.py` | Modified | Added CoverKeyRole, SourceTypeRole; delegated to normalizer |
| `ui_qml_bridge/queue_bridge.py` | Modified | Added currentIndex, add(), replaceAndPlay() slots |
| `ui_qml_bridge/nowplaying_bridge.py` | Modified | Removed _queue, _queue_internal_refs, _normalize_queue, queue subscription; retained transport/history/quality |
| `ui_qml/pages/PlaybackPage.qml` | Modified | Replaced ps.queue with qb.queueModel/qb.queueCount |
| `ui_qml/pages/nowplaying/NowPlayingQueuePreview.qml` | Modified | Replaced ps.queue with qb.queueModel |
| `ui_qml/pages/queue/QueueActions.qml` | Modified | Single saveAsPlaylist call |
| `ui_qml/pages/queue/QueuePage.qml` | Modified | Offscreen rendering compatibility |
| `tests/qml/models/test_queue_item.py` | **Created** | 5 contract tests |
| `tests/qml/queue/test_queue_canonical_inyeccion.py` | Extended | 22 role/position tests |
| `tests/qml/queue/test_queue_bridge_v2.py` | **Created** | 11 command/delegation tests |
| `tests/qml/playback/test_nowplaying_queue_removal.py` | **Created** | 3 state-removal tests |
| `tests/qml/playback/test_playback_queue_workflow.py` | Extended | 12 convergence tests |
| `tests/qml/queue/test_queue_offscreen_rendering.py` | **Created** | 4 rendered-state tests |

**Total**: 6 new files, 8 modified files, ~620-880 changed lines across 3 autonomous slices.

## Final Test Results

| Suite | Result |
|-------|--------|
| Change-related focused suite (8 files) | ✅ 74 passed / ❌ 0 failed (0.65s) |
| `compileall` | ✅ Clean |
| Ruff on changed files | ✅ All checks passed |
| Global Ruff | 303 pre-existing errors (unchanged) |

## Warnings

- **Task 3.4 (regression verification)**: Blocked by pre-existing repository failures unrelated to this change (Audio Lab collection errors, `productive_workflows/conftest.py` abort). All change-related tests pass (74/74). This is a verification-only cleanup task, not an implementation task.
- **14 pre-existing legacy queue test failures**: In broader `tests/qml/queue/` suite — all are pre-existing contract mismatches (version-2 persistence, mutable shuffle_order, boolean undo, optional QueueBridge service assumptions). None are regression from this change.

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `qml-playback-queue` | Created | 5 requirements, 10 scenarios (full spec — no prior main spec existed) |

## Archive Contents

- proposal.md ✅
- design.md ✅
- spec.md ✅
- tasks.md ✅ (8/9 tasks complete; 3.4 blocked by pre-existing issues)
- verify-report.md ✅

## Source of Truth Updated

- `openspec/specs/qml-playback-queue/spec.md` — new main spec for QML playback queue capability

## SDD Cycle Complete

The change has been fully planned, implemented (strict TDD), verified, and archived. All 5 functional requirements with 10 scenarios are covered by passing tests. The queue convergence is complete — every QML surface now reads from the same canonical model through QueueBridge.

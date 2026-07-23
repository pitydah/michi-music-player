# Proposal: QML Playback Queue Convergence

## Intent

Eliminate divergent QML queue projections and duplicate observers so QueueService remains the only queue authority and every queue surface shows the same item identity, ordering, and current-track state.

## Scope

### In Scope
- Gaps 1–2: introduce one typed queue-item projector and make QueueListModel/QueueBridge the sole QML queue-state projection; migrate Now Playing consumers and remove NowPlayingBridge’s queue cache/subscription.
- Gaps 6–7: standardize add versus replace-and-play delegation to QueueService and make save-as-playlist one bridge command/one write.
- Gap 8: add offscreen rendering tests for empty, populated, current, and reordered states.

### Out of Scope
- Gap 3: moving or persisting playback history in QueueService.
- Gap 4: QML context-event tracking.
- Gap 5: broader transport/backend responsibility refactoring.
- Changes to PlayerService, PlaybackController, audio pipelines, Android/sync, or visual design.

## Capabilities

### New Capabilities
- `qml-playback-queue`: Defines one reactive QML queue projection, canonical command semantics, playlist-save behavior, and rendered queue states.

### Modified Capabilities
None; no existing OpenSpec capabilities are present.

## Approach

Create a typed projector under `ui_qml/models/` with a stable superset schema. QueueListModel exposes it; QueueBridge owns queue observation and commands. Migrate PlaybackPage and NowPlayingQueuePreview to `queueModel`/`queueCount`, then remove NowPlayingBridge’s queue cache, normalization, and subscription while retaining transport and history.

Strict TDD precedes each migration. Auto-chain delivery:
1. **First slice (~180–260 changed lines):** projector, complete model roles, schema parity tests; no consumer migration.
2. **Observation convergence (~260–360):** QML consumers and NowPlayingBridge state removal.
3. **Command/render convergence (~180–260):** semantics, single playlist save, QML rendering tests.

Estimated total: **620–880 changed lines**, each slice kept within the 400-line review budget.

## Alternatives Considered

- Core normalization: rejected; QML fields do not belong in QueueService.
- Shared mapper with both observers: safer initially, but preserves duplicate state.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `ui_qml/models/QueueListModel.py` | Modified | Canonical roles/projection |
| `ui_qml_bridge/queue_bridge.py` | Modified | Sole queue observer/commands |
| `ui_qml_bridge/nowplaying_bridge.py` | Modified | Remove duplicate queue state |
| `ui_qml/pages/{queue,nowplaying}/`, `PlaybackPage.qml` | Modified | Consume canonical model |
| `tests/qml/` | Modified | Contract and render coverage |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| List-to-model bindings regress | Medium | Contract tests, compatibility, offscreen rendering |
| Current-index signal drift | Medium | Assert one event yields one model update |
| Oversized review | Medium | Three autonomous slices |

## Rollback Plan

Revert a failing slice independently; retain compatibility delegators until consumer tests pass.

## Dependencies

- Existing QueueService and QML test harness; no new packages.

## Success Criteria

- [ ] Every QML surface exposes identical queue fields and current index.
- [ ] Only QueueService and one QML model hold queue state.
- [ ] Queue mutations and playlist save execute once.
- [ ] Focused and offscreen rendering tests pass.

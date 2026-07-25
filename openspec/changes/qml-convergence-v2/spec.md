# Delta Spec: QML Convergence v2

## Overview

Complete the vertical convergence of Queue and Now Playing in the QML UI so that QueueService is the undisputed single authority, bridges expose clean contracts, signals are granular, QueueListModel is incremental, and all surfaces instantiate and test correctly.

## Baseline Audit Summary

- 13/18 questions PASS, 2 PARTIAL, 3 UNKNOWN (runtime)
- QueueService = single source of truth (AST-enforced)
- QueueBridge = no PlayerService dependency for mutations
- NowPlayingBridge = no local queue
- All5 ingress paths route through QueueService
- Session restore without autoplay

---

## R1: Queue Authority

**Goal:** Eliminate any residual dual-authority patterns.

### Acceptance Criteria
- [ ] QueueService is the only object that mutates queue state
- [ ] NowPlayingBridge has no `queue` property
- [ ] No QML file references `playbackBridge` as primary for queue/transport
- [ ] No polling timers or periodic `refresh()` for state sync
- [ ] No fallback patterns `queueBridge ? queueBridge : nowplayingBridge`

### Scenarios

**Given** a queue with 3 tracks
**When** the user calls `queueBridge.playIndex(1)`
**Then** QueueService.current_index becomes 1
**And** QueueBridge emits currentIndexChanged
**And** NowPlayingBridge emits currentTrackChanged
**And** no other queue state is modified

**Given** NowPlayingBridge is active
**When** the user calls `nowplayingBridge.next()`
**Then** the call is delegated to QueueService.next()
**And** QueueService updates current_index
**And** QueueBridge emits currentIndexChanged
**And** no local queue state exists in NowPlayingBridge

**Given** PlaybackBridge exists as a legacy delegate
**When** any QML component needs transport functionality
**Then** it must use nowplayingBridge as primary
**And** PlaybackBridge is only a thin delegate, not a product reference

---

## R2: QML Contracts (Final)

### QueueBridge Properties

| Property | Type | Source | Signal |
|----------|------|--------|--------|
| items/model | QueueListModel | QueueService | itemsChanged |
| count | int | QueueService.items.length | countChanged |
| currentIndex | int | QueueService.current_index | currentIndexChanged |
| currentToken | string | QueueService.current_token | currentTokenChanged |
| repeatMode | string | QueueService.repeat_mode | repeatModeChanged |
| shuffleEnabled | bool | QueueService.shuffle_enabled | shuffleEnabledChanged |
| totalDuration | int | computed from items | durationSummaryChanged |
| remainingDuration | int | computed from items + index | durationSummaryChanged |
| canUndo | bool | QueueService.can_undo | undoAvailabilityChanged |
| hasMissingTracks | bool | QueueService.missing_tracks | operationPendingChanged |
| missingTrackCount | int | QueueService.missing_count | operationPendingChanged |
| operationPending | bool | QueueService.operation_pending | operationPendingChanged |
| errorMessage | string | QueueService.error | errorMessageChanged |
| revision | int | QueueService.revision | itemsChanged |

### QueueBridge Commands

| Command | Parameters | Returns |
|---------|-----------|---------|
| playIndex | index: int | dict {ok, error?} |
| removeFromQueue | index: int | dict {ok, error?} |
| removeByToken | token: string | dict {ok, error?} |
| moveItem | from: int, to: int | dict {ok, error?} |
| clearQueue | - | dict {ok, error?} |
| toggleShuffle | - | dict {ok, error?} |
| setRepeatMode | mode: string | dict {ok, error?} |
| undo | - | dict {ok, error?} |
| saveAsPlaylist | name: string | dict {ok, playlist_id?, error?} |
| retryMissingTracks | - | dict {ok, retried: int, error?} |

### NowPlayingBridge Properties

| Property | Type | Source | Signal |
|----------|------|--------|--------|
| currentTrack | dict | QueueService.current + PlayerService | currentTrackChanged |
| title | string | currentTrack.title | currentTrackChanged |
| artist | string | currentTrack.artist | currentTrackChanged |
| album | string | currentTrack.album | currentTrackChanged |
| artwork | string | currentTrack.cover_key | currentTrackChanged |
| duration | int | PlayerService.duration | durationChanged |
| position | int | PlayerService.position | positionChanged |
| playbackState | string | PlayerService.state | playbackStateChanged |
| volume | int | PlayerService.volume | volumeChanged |
| muted | bool | PlayerService.muted | mutedChanged |
| canSeek | bool | PlayerService.can_seek | capabilitiesChanged |
| canGoPrevious | bool | QueueService.current_index > 0 | capabilitiesChanged |
| canGoNext | bool | QueueService.current_index < count-1 | capabilitiesChanged |
| commandPending | bool | PlayerService.command_pending | commandStateChanged |
| errorMessage | string | PlayerService.error | errorChanged |

### NowPlayingBridge Commands

| Command | Parameters | Returns |
|---------|-----------|---------|
| play | - | dict {ok, error?} |
| pause | - | dict {ok, error?} |
| togglePlayPause | - | dict {ok, error?} |
| stop | - | dict {ok, error?} |
| previous | - | dict {ok, error?} |
| next | - | dict {ok, error?} |
| seek | position: int | dict {ok, error?} |
| setVolume | volume: int | dict {ok, error?} |
| toggleMute | - | dict {ok, error?} |

---

## R3: Granular Signals

### QueueBridge Signal Rules

**Given** only currentIndex changes
**When** the signal fires
**Then** only currentIndexChanged is emitted
**And** dataChanged fires for exactly 2 rows (old index, new index)
**And** itemsChanged is NOT emitted
**And** countChanged is NOT emitted

**Given** a track is added to the queue
**When** the signal fires
**Then** itemsChanged is emitted
**And** countChanged is emitted
**And** durationSummaryChanged is emitted
**And** currentIndexChanged is NOT emitted (unless index shifts)

**Given** shuffle is toggled
**When** the signal fires
**Then** shuffleEnabledChanged is emitted
**And** itemsChanged is emitted (order changed)
**And** currentIndexChanged is emitted (current track may shift)

### NowPlayingBridge Signal Rules

**Given** only position changes during playback
**When** the signal fires
**Then** only positionChanged is emitted
**And** currentTrackChanged is NOT emitted
**And** playbackStateChanged is NOT emitted

**Given** the user changes volume
**When** the signal fires
**Then** only volumeChanged is emitted
**And** no other signals fire

---

## R4: Incremental QueueListModel

### Acceptance Criteria
- [ ] currentIndex change uses dataChanged (2 rows), NOT beginResetModel
- [ ] Track addition uses beginInsertRows/endInsertRows
- [ ] Track removal uses beginRemoveRows/endRemoveRows
- [ ] Track move uses beginMoveRows/endMoveRows
- [ ] Full reset only for complete queue replacement or restore
- [ ] Scroll position preserved after non-structural changes
- [ ] Keyboard focus preserved after non-structural changes

### Scenarios

**Given** a QueueListModel with 100 tracks
**When** currentIndex changes from 5 to 10
**Then** dataChanged is emitted for row 5 and row 10
**And** beginResetModel is NOT called
**And** scroll position is unchanged
**And** keyboard focus is unchanged

**Given** a QueueListModel with 100 tracks
**When** a track at index 20 is removed
**Then** beginRemoveRows is called for index 20
**And** rows 21-99 shift down
**And** currentIndex is adjusted if needed
**And** dataChanged is emitted for the new current row

**Given** a QueueListModel with 100 tracks
**When** the entire queue is replaced (restore)
**Then** beginResetModel is called
**And** all data is refreshed
**And** currentIndex is set to restored value

---

## R5: QueuePage Runtime

### Acceptance Criteria
- [ ] QueuePage.qml instantiates without errors in QQmlComponent
- [ ] No `root.*` references to undeclared properties
- [ ] No null Connections blocks
- [ ] No missing imports
- [ ] Foundations: MichiPage, MichiPageHeader, PageStateManager
- [ ] States: LOADING, READY, EMPTY, ERROR (mutually exclusive)
- [ ] operationPending does NOT trigger full-page loading

### States

**Given** the queue service is initializing
**When** QueuePage renders
**Then** state is LOADING
**And** a loading indicator is shown

**Given** the queue is empty and service is ready
**When** QueuePage renders
**Then** state is EMPTY
**And** an empty state message is shown
**And** "Add music" action is available

**Given** the queue has tracks and service is ready
**When** QueuePage renders
**Then** state is READY
**And** the track list is shown

**Given** a queue operation fails
**When** QueuePage renders
**Then** state is ERROR
**And** an error message is shown
**And** retry action is available

**Given** operationPending is true (e.g., shuffle in progress)
**When** QueuePage renders
**Then** state remains READY (not LOADING)
**And** individual controls show pending state

---

## R6: NowPlaying Runtime

### Acceptance Criteria
- [ ] NowPlayingPage.qml instantiates without errors
- [ ] NowPlayingBar.qml instantiates without errors
- [ ] Only nowplayingBridge is used (no playbackBridge product refs)
- [ ] commandPending blocks only the affected control, not the page
- [ ] States: LOADING, EMPTY, READY, ERROR

### Scenarios

**Given** no track is playing
**When** NowPlayingPage renders
**Then** state is EMPTY
**And** a placeholder message is shown

**Given** a track is playing
**When** NowPlayingPage renders
**Then** state is READY
**And** currentTrack properties are displayed

**Given** the user presses play
**When** commandPending is true
**Then** only the play button shows loading state
**And** other controls remain interactive

---

## R7: Session Continuity

### Acceptance Criteria
- [ ] Queue, tokens, currentIndex, track identity, repeat, shuffle, position are saved
- [ ] Restoration does NOT trigger autoplay
- [ ] Canonical resolver resolves tracks
- [ ] Unresolvable tracks marked as available: false
- [ ] currentIndex remapped after resolve/filter
- [ ] Position restored only for same track identity
- [ ] Position limited to valid duration range

### Scenarios

**Given** a session with 50 tracks, index 10, position 45s
**When** the application restarts
**Then** the queue is restored with 50 tracks
**And** currentIndex is 10
**And** position is 45s
**And** playback is paused (not playing)

**Given** a restored track has a stale filepath
**When** the resolver cannot find the file
**Then** the track is marked available: false
**And** the track remains in the queue
**And** currentIndex is adjusted if the missing track was current

**Given** a restored track has a different duration
**When** the session is restored
**Then** position is clamped to min(saved_position, new_duration)

---

## R8: Ingress from All Surfaces

### Acceptance Criteria
- [ ] Library "play" calls QueueService.replace_and_play()
- [ ] Playlist "play" calls QueueService.replace_and_play()
- [ ] Mix "play" calls QueueService.enqueue() or replace_and_play()
- [ ] AI "play" calls QueueService.enqueue()
- [ ] Michi Link "play" calls QueueService.enqueue() or replace_and_play()
- [ ] No QML → PlayerService.queue direct access
- [ ] No QML → NowPlayingBridge.localQueue access

### Scenarios

**Given** the user clicks a track in Library
**When** the play action is triggered
**Then** QueueService.replace_and_play() is called
**And** QueueBridge updates immediately
**And** NowPlayingBridge reflects the new track
**And** QueuePage shows the new track as current

---

## R9: Tests

### Unit Tests
- QueueItem: all fields, defaults, as_dict(), equality
- QueueService: add, remove, move, clear, undo, shuffle, repeat, index, missing, restore
- QueueBridge: all commands, signal emissions, error handling
- QueueListModel: data(), roleNames(), incremental updates, structural changes
- NowPlayingBridge: all properties, all commands, signal emissions

### Signal Tests
- Verify exact signals emitted for each mutation
- Verify no unrelated signals fire
- Verify dataChanged for exactly the right rows

### Runtime QML Tests
- QueuePage.qml instantiation via QQmlComponent
- NowPlayingPage.qml instantiation
- NowPlayingBar.qml instantiation
- All sub-components instantiate
- No binding errors in Qt message handler

### Vertical Integration Tests
- Library → QueueService → QueueBridge → QueueListModel → QueuePage
- Queue current change → PlayerService → NowPlayingBridge → NowPlayingPage → NowPlayingBar
- Session restore → QueueService → QueueBridge → QML state

### Performance Tests
- 100 tracks: measure load time, signal count
- 1000 tracks: measure load time, signal count, scroll stability
- 5000 tracks: measure load time, index change time, memory usage

---

## R10: Accessibility

### Acceptance Criteria
- [ ] All interactive controls have Accessible.name
- [ ] Contextual controls have Accessible.description
- [ ] Focus is visible on all interactive elements
- [ ] Tab navigation follows logical order
- [ ] Enter and Space activate controls
- [ ] Repeat, shuffle, remove, clear, undo, save have labels
- [ ] Current track is announced
- [ ] Missing track is announced

---

## Scope Limits

Do NOT modify:
- QtWidgets legacy
- window.py legacy
- Audio Lab
- Michi Micro Server / Mobile / Big Server
- Global theme system
- Global navigation
- Ruff global config
- Unrelated tests
- Plugin architecture
- Video modules
- Lyrics

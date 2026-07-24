# qml-playback-queue Specification

## Purpose

Define one reactive QML projection and command boundary for `QueueService` without changing playback, Android/sync, persistence, history, or visual design.

## Functional Requirements

### Requirement: Canonical queue item contract

`QueueListModel` MUST expose every item with these QML roles and types: `trackId:string`, `trackUid:string`, `title:string`, `artist:string`, `album:string`, `albumKey:string`, `duration:int`, `current:bool`, `position:int`, `coverKey:string`, and `sourceType:string`. Missing values MUST use `""`, `0`, or `false`; `position` MUST equal the zero-based model row and exactly one item MAY be current.

#### Scenario: Dict and object inputs converge
- GIVEN equivalent dict and object queue items with optional fields missing
- WHEN each item is projected at the same position and current index
- THEN both projections contain the complete role set with identical typed values
- AND neither projection exposes source objects or private file references

#### Scenario: Current item follows service state
- GIVEN a populated queue whose `current_index` changes
- WHEN `QueueService` publishes the new state
- THEN `current` is true only at that index and `position` remains aligned with ordering

### Requirement: Single QML queue observation

`QueueService` MUST remain authoritative; `QueueListModel` MUST hold the sole QML queue projection, while `QueueBridge` MUST expose `queueModel`, `queueCount`, and `currentIndex`. `NowPlayingBridge` MUST NOT cache, normalize, or subscribe to queue state and SHALL retain transport and history only. `PlaybackPage` and `NowPlayingQueuePreview` MUST consume `QueueBridge` state.

#### Scenario: One domain event updates all surfaces
- GIVEN QueuePage, PlaybackPage, and NowPlayingQueuePreview are active
- WHEN one queue reorder event is published
- THEN each surface shows the same order, count, and current item after one model update
- AND no second queue projection or NowPlayingBridge queue notification occurs

#### Scenario: Queue bridge is unavailable
- GIVEN a queue-consuming surface has no `QueueBridge`
- WHEN it renders
- THEN it shows an empty or unavailable state without accessing the database or crashing

### Requirement: Distinct queue ingress semantics

`QueueBridge.add(items)` MUST append through `QueueService.enqueue(..., play_now=False)` without changing the current item. `QueueBridge.replaceAndPlay(items, startIndex)` MUST delegate once to `QueueService.replace_and_play`; it MUST reject empty items or an invalid index without mutation. Existing queue-item commands MUST delegate once to `QueueService` and return its structured result.

#### Scenario: Add preserves playback
- GIVEN an active queue
- WHEN QML invokes `add(items)`
- THEN items are appended once and the current index is unchanged

#### Scenario: Replace and play is atomic
- GIVEN valid items and start index
- WHEN QML invokes `replaceAndPlay(items, startIndex)`
- THEN the queue is replaced once and playback starts at that index

#### Scenario: Invalid replacement is rejected
- GIVEN empty items or an out-of-range start index
- WHEN QML invokes `replaceAndPlay`
- THEN it returns a stable error and leaves queue and playback unchanged

### Requirement: Single playlist save

`QueueBridge.saveAsPlaylist(name)` MUST be the only QML save command and MUST perform exactly one playlist write using the current canonical queue. Blank names, unavailable playlist services, empty queues, and write failures MUST return `{ok:false,error:string,message?:string}` without a second save attempt.

#### Scenario: Successful named save
- GIVEN a non-empty queue and valid name
- WHEN either queue save control invokes `saveAsPlaylist`
- THEN exactly one playlist is created with current queue order

#### Scenario: Save precondition fails
- GIVEN a blank name, empty queue, or unavailable playlist service
- WHEN QML requests a save
- THEN no write occurs and a structured error is returned

### Requirement: Rendered queue states

Queue surfaces MUST render empty, populated, current, and reordered states offscreen using the canonical model. They MUST preserve existing theme, accessibility, keyboard, responsive, no-parent-opacity, no-list-blur, and no-per-item-shadow constraints.

#### Scenario: Reordered state renders safely
- GIVEN a populated offscreen QueuePage
- WHEN the model is reordered
- THEN delegate order and current styling update without QML warnings or stale rows

## Non-functional and Test Requirements

- Strict TDD SHALL apply per slice: focused tests MUST fail before production changes, then pass before refactoring.
- Tests MUST cover projector defaults/types, model roles, one-event/one-update observation, subscription teardown, command delegation counts/errors, single-write saving, and offscreen states.
- Verification MUST include focused queue tests and `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/ -q`; no new dependency is permitted.

## Acceptance Criteria

- Gap 1: all queue surfaces use the complete canonical role contract.
- Gap 2: only `QueueListModel` projects queue state for QML; `NowPlayingBridge` has no queue observer/cache.
- Gap 6: append and replace-and-play are distinct, single-delegation commands.
- Gap 7: each save gesture causes at most one playlist write.
- Gap 8: all four rendered states pass offscreen without warnings or stale data.

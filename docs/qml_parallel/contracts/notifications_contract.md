<<<<<<< Updated upstream
# NotificationBridge Integration Contract
=======
<<<<<<< HEAD
# Notification Bridge Contract
>>>>>>> Stashed changes

## Context Property
- `notificationBridge` → `NotificationBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `currentNotification` | `QVariant` (dict or None) | `notificationChanged` |
| `queueLength` | `int` | `notificationCountChanged` |
| `persistentNotifications` | `QVariantList` | `notificationChanged` |

Notification dict schema: `{id: str, text: str, kind: str, timestamp: float, action: str, persistent: bool, progress: int, job_id: str, _dedup_key: str, _priority: int, _timeout_ms: int}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `showMessage` | `dict` | `text: str`, `kind: str = "info"` |
| `showAction` | `dict` | `text: str`, `action: str`, `kind: str = "info"` |
| `showProgress` | `dict` | `text: str`, `job_id: str`, `progress: int`, `kind: str = "info"` |
| `dismiss` | (none) | none |
| `clear` | (none) | none |
| `executeCurrentAction` | `dict` | none |
| `executeNotificationAction` | `dict` | `notification_id: str` |
| `openJob` | `dict` | `job_id: str` |
| `cancelJobById` | `dict` | `job_id: str` |
| `retry` | `dict` | `notification_id: str` |
| `retryJob` | `dict` | `job_id: str` |
| `undoAction` | `dict` | `undo_key: str` |
| `showTrack` | `dict` | `track_id: int`, `album_key: str = ""` |
| `showDevice` | `dict` | `device_id: str` |
| `openDiagnostics` | `dict` | none |
| `openSettings` | `dict` | none |
| `updateProgress` | `dict` | `job_id: str`, `progress: float`, `text: str = ""` |
| `notificationScore` | `dict` | none |

All slots returning `dict` include `ok: bool`. Error responses include `error` string.

## Signals
| Signal | Payload |
|---|---|
| `notificationChanged` | (none) |
| `notificationCountChanged` | (none) |
| `actionExecuted` | `action_id: str, result: dict` |

## Models Exposed
None.

## Error Types/Codes
- `"NO_CURRENT_NOTIFICATION"` — no current notification for action
- `"NO_ACTION"` — notification has no action_id
- `"NOT_FOUND"` — notification_id not found
- `"INVALID_TRACK"` — track_id malformed
- `"NO_NAVIGATION_TARGET"` — no bridge for openJob
- `"UNSUPPORTED"` — job bridge missing for cancel/retry
- `"NO_ACTION_REGISTRY"` — fallback for action execution

## States
None exposed. Internal queue state managed via `_current`, `_queue`, `_persistent_map`.

## Lifecycle Expectations
- `_next()` sorts queue by priority (descending), promotes highest to `_current`.
- Non-persistent notifications auto-dismiss after `_DEFAULT_TIMEOUT_MS` (5000ms).
- Persistent notifications (kind="error", showAction, showProgress) stay until explicitly dismissed.
- Max queue length: 20; overflow discards from front.
- Deduplication by `_dedup_key`: if same key exists, updates text/timestamp instead of creating duplicate.

## Behavior When Services Are Missing/Null
- `_action_registry` None: `_execute_action` falls through to `NO_ACTION_REGISTRY` for unknown actions.
- `_job_bridge` None: `openJob` falls back to `NavigationBridge`; `cancelJobById`/`retryJob` return `UNSUPPORTED`.
- `_navigation_bridge` None: navigation actions fall back to `ActionRegistry`.

## Destructive Actions and Confirmations
None in bridge itself — destructive actions delegated via `ActionRegistry`.

## Cancellation Contract
- `dismiss()` clears current notification, stops timeout timer, advances queue.
- `clear()` empties entire queue and all maps.

<<<<<<< Updated upstream
=======
## Destructive Action Handling
- `clear()` is destructive with no undo
- `undoAction()` provides limited undo via `action_registry.execute("undo_<key>")`
=======
# NotificationBridge Integration Contract

## Context Property
- `notificationBridge` → `NotificationBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `currentNotification` | `QVariant` (dict or None) | `notificationChanged` |
| `queueLength` | `int` | `notificationCountChanged` |
| `persistentNotifications` | `QVariantList` | `notificationChanged` |

Notification dict schema: `{id: str, text: str, kind: str, timestamp: float, action: str, persistent: bool, progress: int, job_id: str, _dedup_key: str, _priority: int, _timeout_ms: int}`

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `showMessage` | `dict` | `text: str`, `kind: str = "info"` |
| `showAction` | `dict` | `text: str`, `action: str`, `kind: str = "info"` |
| `showProgress` | `dict` | `text: str`, `job_id: str`, `progress: int`, `kind: str = "info"` |
| `dismiss` | (none) | none |
| `clear` | (none) | none |
| `executeCurrentAction` | `dict` | none |
| `executeNotificationAction` | `dict` | `notification_id: str` |
| `openJob` | `dict` | `job_id: str` |
| `cancelJobById` | `dict` | `job_id: str` |
| `retry` | `dict` | `notification_id: str` |
| `retryJob` | `dict` | `job_id: str` |
| `undoAction` | `dict` | `undo_key: str` |
| `showTrack` | `dict` | `track_id: int`, `album_key: str = ""` |
| `showDevice` | `dict` | `device_id: str` |
| `openDiagnostics` | `dict` | none |
| `openSettings` | `dict` | none |
| `updateProgress` | `dict` | `job_id: str`, `progress: float`, `text: str = ""` |
| `notificationScore` | `dict` | none |

All slots returning `dict` include `ok: bool`. Error responses include `error` string.

## Signals
| Signal | Payload |
|---|---|
| `notificationChanged` | (none) |
| `notificationCountChanged` | (none) |
| `actionExecuted` | `action_id: str, result: dict` |

## Models Exposed
None.

## Error Types/Codes
- `"NO_CURRENT_NOTIFICATION"` — no current notification for action
- `"NO_ACTION"` — notification has no action_id
- `"NOT_FOUND"` — notification_id not found
- `"INVALID_TRACK"` — track_id malformed
- `"NO_NAVIGATION_TARGET"` — no bridge for openJob
- `"UNSUPPORTED"` — job bridge missing for cancel/retry
- `"NO_ACTION_REGISTRY"` — fallback for action execution

## States
None exposed. Internal queue state managed via `_current`, `_queue`, `_persistent_map`.

## Lifecycle Expectations
- `_next()` sorts queue by priority (descending), promotes highest to `_current`.
- Non-persistent notifications auto-dismiss after `_DEFAULT_TIMEOUT_MS` (5000ms).
- Persistent notifications (kind="error", showAction, showProgress) stay until explicitly dismissed.
- Max queue length: 20; overflow discards from front.
- Deduplication by `_dedup_key`: if same key exists, updates text/timestamp instead of creating duplicate.

## Behavior When Services Are Missing/Null
- `_action_registry` None: `_execute_action` falls through to `NO_ACTION_REGISTRY` for unknown actions.
- `_job_bridge` None: `openJob` falls back to `NavigationBridge`; `cancelJobById`/`retryJob` return `UNSUPPORTED`.
- `_navigation_bridge` None: navigation actions fall back to `ActionRegistry`.

## Destructive Actions and Confirmations
None in bridge itself — destructive actions delegated via `ActionRegistry`.

## Cancellation Contract
- `dismiss()` clears current notification, stops timeout timer, advances queue.
- `clear()` empties entire queue and all maps.

>>>>>>> Stashed changes
## Integration with JobService
- `openJob(job_id)`: navigates to JobBridge (via `navigateToJob`).
- `cancelJobById(job_id)`: calls `JobBridge.cancelJob(job_id)`.
- `retryJob(job_id)`: calls `JobBridge.retryJob(job_id)`.
- `updateProgress(job_id, progress, text)`: updates or creates progress notification deduplicated by `progress:{job_id}`.

## Integration with ActionRegistry
- `_execute_action(action_id)`: delegates unknown action IDs to `ActionRegistry.execute()`.
- Action ID conventions: `"navigate_jobs"`, `"navigate_home_audio"`, `"navigate_diagnostics"`, `"navigate_settings"`, `"track_open_album"`.

## Integration with NavigationBridge
- `openJob` → `navigation_bridge.navigate("audio_lab.jobs")`
- `showTrack` (with album) → `navigation_bridge.navigateWithParams("library.album_detail", ...)`
- `showDevice` → `navigation_bridge.navigate("home_audio")`
- `openDiagnostics` → `navigation_bridge.navigate("diagnostics")`
- `openSettings` → `navigation_bridge.navigate("settings.general")`

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED.

## Integration with AccessibilityBridge
NOT IMPLEMENTED — basic `QAccessible` announcement attempted in `_announce()`.
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

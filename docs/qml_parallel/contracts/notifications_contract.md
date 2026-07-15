# Notification Bridge Contract

## Context Property
`NotificationBridge` registered as `notification` context property.

## Class Name
`NotificationBridge` (`ui_qml_bridge/notification_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `action_registry` | `ActionRegistry \| None` | `None` |
| `job_bridge` | `JobBridge \| None` | `None` |
| `notification_service` | `NotificationService \| None` | `None` |
| `navigation_bridge` | `NavigationBridge \| None` | `None` |
| `diagnostics_service` | `Any \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `currentNotification` | `QVariant` | `notificationChanged` | Currently displayed notification dict or None |
| `queueLength` | `int` | `notificationCountChanged` | Number of queued notifications |
| `persistentNotifications` | `QVariantList` | `notificationChanged` | List of persistent (non-dismissable by timeout) notifications |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `showMessage` | `text: str, kind: str="info", persistent: bool=None` | `dict` | Queue a text notification; persistent auto-true for errors |
| `showAction` | `text: str, action: str, kind: str="info"` | `dict` | Queue an action notification (persistent, high priority) |
| `showProgress` | `text: str, job_id: str, progress: int, kind: str="info"` | `dict` | Queue or update a progress notification |
| `dismiss` | `notification_id: str=""` | `dict` | Dismiss current or specified notification |
| `clear` | — | `void` | Clear all notifications, queue, dedup map, persistent map |
| `executeCurrentAction` | — | `dict` | Execute the action attached to the current notification |
| `executeNotificationAction` | `notification_id: str` | `dict` | Execute action on a specific notification |
| `updateProgress` | `job_id: str, progress: float, text: str=""` | `dict` | Update progress on an active job notification |
| `openJob` | `job_id: str` | `dict` | Navigate to job detail view |
| `cancelJobById` | `job_id: str` | `dict` | Cancel a job by ID via JobBridge |
| `retry` | `notification_id: str` | `dict` | Retry the action in a notification |
| `retryJob` | `job_id: str` | `dict` | Retry a job via JobBridge |
| `undoAction` | `undo_key: str` | `dict` | Execute undo for a given action key |
| `showTrack` | `track_id: int, album_key: str=""` | `dict` | Navigate to album detail or execute track_open_album action |
| `showDevice` | `device_id: str` | `dict` | Navigate to home_audio section |
| `openDiagnostics` | — | `dict` | Navigate to diagnostics section |
| `openSettings` | — | `dict` | Navigate to settings.general section |
| `notificationScore` | — | `dict` | Return capability score (0-100) with sub-metrics |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `notificationChanged` | — | Current or persistent notification state changed |
| `notificationCountChanged` | — | Queue length changed |
| `actionExecuted` | `str action_id, dict result` | An action was executed from a notification |

## Models Exposed
None. Notifications are dict-based with fields: `id, text, kind, timestamp, action, persistent, progress, job_id`.

## Error Handling
- All public slots return `dict` with `ok: bool`
- Error codes: `"NO_CURRENT_NOTIFICATION"`, `"NO_ACTION"`, `"NOT_FOUND"`, `"NO_NAVIGATION_TARGET"`, `"UNSUPPORTED"`, `"INVALID_TRACK"`
- Action execution delegates to `_execute_action()` which falls through `action_registry`

## Error Codes
- `NO_CURRENT_NOTIFICATION` — no current notification to act on
- `NO_ACTION` — notification has no action_id
- `NOT_FOUND` — notification_id doesn't match any in queue/persistent
- `UNSUPPORTED` — required bridge/service not available
- `NO_ACTION_REGISTRY` — action_registry not injected
- `NO_NAVIGATION_TARGET` — no navigation bridge or action fallback

## States
- `currentNotification` is `None` when idle, a dict when active
- Notifications have `kind`: `"info"`, `"success"`, `"warning"`, `"error"`
- Queue priority sorting: high priority first, then insertion order

## Lifecycle
- Created by `BridgeFactory.create_notification_bridge()` with action_registry + job_bridge
- Subscribes to `NotificationService.on()` if provided (service notifications forwarded to bridge)
- Internal `_timeout_timer` auto-advances non-persistent notifications after 5s
- Queue auto-prunes at max 20 items; `_next()` pops highest-priority item

## Behavior When Service Is Null/Missing
- All services optional; bridge works standalone
- Without `notification_service`: bridge acts as standalone notification queue
- Without `action_registry`: built-in action routing (openJob, cancelJob, undo, openTrack, openAlbum, openDevice, openDiagnostics, openSettings) still works
- Without `job_bridge`: job-related actions return `"UNSUPPORTED"`
- Without `navigation_bridge`: navigation falls back to action_registry

## Integration
- **JobService**: `openJob`, `cancelJobById`, `retryJob` delegate to `job_bridge`
- **ActionRegistry**: `_execute_action` falls through to registry for unrecognized action IDs
- **NavigationBridge**: Used for `openJob`, `showTrack`, `showDevice`, `openDiagnostics`, `openSettings`
- **CapabilityBridge**: `has_notification_service` checked in wiring assertions

## Cancellation Contract
- `dismiss()` clears the current notification
- `clear()` empties entire system
- Progress updates use dedup key `progress:{job_id}`
- Timeout timer stopped on `dismiss`/`clear`

## Destructive Action Handling
- `clear()` is destructive with no undo
- `undoAction()` provides limited undo via `action_registry.execute("undo_<key>")`

# Radio Core V2 — Integration Plan

This document describes how Radio Core V2 integrates with other subsystems.
Changes listed here are **pending** and should not be implemented in this branch
(`feature/radio-core-v2`). They will be done in subsequent branches.

## 1. RadioBridge QML

**When:** After this branch merges.

**What:**
- Create `ui_qml_bridge/radio_bridge.py` that wraps `RadioService`
- Expose `Station` models as `QVariantMap` lists
- Connect `EventBus` to QML signals

**Pending changes in:**
- `ui_qml_bridge/` — new file: `radio_bridge.py`
- `ui_qml/pages/radio/` — new QML page

## 2. QtWidgets Legacy (RadioPage)

**When:** After this branch merges.

**What:**
- Replace `RadioWidget` internal logic with `RadioService` calls
- Remove direct `RadioManager` usage from `streaming/radio_widget.py`
- Wire `EventBus` to Qt signals for UI updates

**Pending changes in:**
- `ui/controllers/radio_controller.py` (if exists) or create
- `streaming/radio_widget.py` — refactor to use RadioService

## 3. Michi AI

**When:** After this branch merges.

**What:**
- Add radio-related actions: "play radio", "search stations"
- Consume `RadioService.search_stations()` and `RadioService.start_station()`

**Pending changes in:**
- `michi_ai/` — add radio action handlers

## 4. Command Palette

**When:** After this branch merges.

**What:**
- Add global commands: "Play radio", "Search station", "Favorites"
- Consume `RadioService` via existing command infrastructure

**Pending changes in:**
- `core/command_palette.py` or equivalent

## 5. Notifications

**When:** After this branch merges.

**What:**
- Subscribe to `RadioService.event_bus` for `session_state_changed` and `playback_failed`
- Show toast on reconnect, error, or metadata change

**Pending changes in:**
- `core/notification_service.py` — add radio event handlers

## 6. Settings (Preferences)

**When:** After this branch merges.

**What:**
- Add radio-specific settings (reconnect config, history retention)
- Read/write via `ReconnectPolicyConfig`

**Pending changes in:**
- `ui/settings_pages.py` — add radio settings page or section
- `core/settings_manager.py` — add radio defaults

## 7. `core/paths.py`

**Required change:**
- Add `radio_db_path()` function returning path to radio database

## 8. `streaming/radio_manager.py`

**Deprecation:**
- `RadioManager` and `RadioStation` (old dataclass) should be deprecated
- Migration path: export old JSON → import via `RadioImportService`

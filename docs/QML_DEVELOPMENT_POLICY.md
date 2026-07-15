# QML Development Policy

**Effective immediately.** This document defines the mandatory policy for all future development on Michi Music Player.

## 1. QML is the only productive UI

All new user interface features must be implemented exclusively in QML.
QtWidgets is frozen and will not receive new views, dialogs, menus or functionality.

## 2. Core/business logic is UI-agnostic

All domain logic must live in `core/services/` or `core/library/`.
Services must not import `ui`, `ui_qml`, or any Qt widget module.

## 3. Bridges are thin adapters

Bridges (in `ui_qml_bridge/`) only adapt QML to services.
Bridges must not:
- Create services, repositories, or database connections
- Import QWidget, QDialog, or QtWidgets
- Maintain secondary state stores
- Execute SQL or business transactions

## 4. No new QtWidgets code

- No new QtWidgets pages, dialogs, menus or views.
- No rewrites of existing QtWidgets code for parity.
- No new dependencies on `PySide6.QtWidgets` from QML runtime.
- No new imports of `ui.*` from `core/`.

## 5. ServiceContainer is the single composition

`core/service_container.py` provides the only productive dependency injection.
`ServiceBundle` and manual composition in `qml_main.py` are deprecated.

## 6. Jobs and processes

All long-running operations must use `JobService` + `ProcessController`.
No blocking `subprocess.run()` or `communicate()` on the UI thread.

## 7. Confirmation for destructive actions

All destructive actions require explicit user confirmation.
See `core/confirmation_service.py`.

## 8. Audio-only

Michi Music Player remains audio-only.
Video playback, conversion, sync, or thumbnails are prohibited.

## 9. Legacy widget access

QtWidgets (legacy) is available only via:
```bash
michi-widgets
```
It is not imported, packaged, or navigated to from the QML runtime.

## 10. Physical audio validation

Physical audio hardware validation is deferred until QML functional parity is demonstrated and stable.
No physical claim should be made without 21/21 verified checks.

## Exceptions

Exceptions to this policy require documented approval and a migration plan.

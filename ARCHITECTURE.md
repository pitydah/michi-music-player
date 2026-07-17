# Architecture

## Layers

```
QML (ui_qml/)
  ↓ Bridges (ui_qml_bridge/)
  ↓ Services (core/)
  ↓ Backends (audio/backends/)
  ↓ GStreamer / MPD
```

## Key Patterns

- **Dependency Injection**: Services receive dependencies via constructors
- **ObservableServiceContainer**: All services observable via state_changed signal
- **ActionRegistry**: All user actions registered with validation
- **AudioBackend Protocol**: GStreamer and MPD implement the same contract
- **Formal Migrations**: Versioned, rollback-capable DB migrations

## Ventanas
- Main.qml: Window con flags, fullscreen (F11), persistencia de tamaño
- AppShell.qml: Sidebar redimensionable, header con drag

## Notificaciones
- NotificationToast: toast temporales
- NotificationCenter: centro de notificaciones con agrupacion
- NotificationBridge: puente con limite de 50 items

## UI/UX
- ThemeStore: modo oscuro/claro, alto contraste, fontScale
- RouteTransition: animaciones entre paginas
- Sidebar: tooltips en modo colapsado, badge de notificaciones

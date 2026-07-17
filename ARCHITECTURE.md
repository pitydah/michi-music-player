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

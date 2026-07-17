# Global Stabilization Baseline

## Metadata
- SHA: 1e5b2a02
- Date: 2026-07-17
- Branch: feature/qml-nowplaying-legacy-parity

## Audit Results

### 1. Code Quality
- Ruff: 129 errors
- Compileall: 0 errors

### 2. Tests
- Total tests: 14631/14636 tests collected (5 deselected), 39 errors
- QML tests: 10910 tests collected, 3 errors

### 3. QML
- QML files: 408
- Components: 121
- Pages: 266

### 4. Services
- Total services: 92
- Registered in container: 13

### 5. Audio Backend
- GStreamerEngine: 64 methods
- GStreamerAudioBackend: 23 methods
- AudioBackend Protocol: 18 methods
- Pipeline instances: 37

### 6. Actions
- Registered: 1
- Duplicates: 0

### 7. Known Issues
- Except Exception pass: 0
- Return ok True without verification: 210
- Bridges accessing DB: 58

### 8. Packaging
- ui_qml in wheel: True
- Wheel built: no

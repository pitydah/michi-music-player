# Writing Tests — Rules & Patterns

## File placement

| Test type | Location |
|-----------|----------|
| E2E bridge workflow | `tests/qml/productive_workflows/test_<domain>_e2e.py` |
| QML component | `tests/qml/negative/test_<domain>.py` |
| Core service | `tests/test_<service>.py` |

## Naming

```
test_<domain>_<action>.py
class Test<Domain><Action>:
    def test_<scenario>(self, ...):
```

## Required fixtures

For `productive_workflows/` tests:

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `bootstrap` | module | Creates AppContext and bridge container |
| `bridges` | function | Dict of bridges for the test |
| `all_bridges` | function | Full bridge registry |
| `nav` | function | NavigationBridge for route asserts |
| `root_window` | module | QQuickWindow for QML interaction |

## Assert patterns

```python
# Return type check
result = bridge.method()
assert isinstance(result, dict)
assert "ok" in result

# Truthy check (not is not False)
assert result.get("ok") is True

# Method existence
assert callable(getattr(bridge, 'methodName', None))

# Navigation
nav.navigate("library")
assert nav.currentRoute == "library"
```

## Markers

Every test file must have `pytestmark`:

```python
pytestmark = [
    pytest.mark.qml_module("<module>"),
    pytest.mark.qml_dimension("<dimension>"),
]
```

Dimensions: `vertical_workflow`, `end_to_end`, `unit`.

## Anti-patterns (DO NOT)

- `hasattr(obj, 'method')` — use `callable(getattr(obj, 'method', None))`
- `is not False` — use `is True`
- `isinstance(result, dict)` without `"ok" in result` — add both
- `time.sleep()` — use `QTest.qWait()` or `wait_for_condition()`
- `pytest.skip()` to hide Qt crashes — classify as CRASH instead

## CI contract

Tests must pass under `QT_QPA_PLATFORM=offscreen`. Qt crashes (134/139) are expected and tracked separately. Tests in `productive_workflows/` must pass under Xvfb.

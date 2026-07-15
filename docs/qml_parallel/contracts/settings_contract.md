# Settings Bridge Contract

## Context Property
`SettingsBridgeV2` registered as both `settings` and `settings_v2` context properties (same object).

## Class Name
`SettingsBridgeV2` (`ui_qml_bridge/settings_bridge_v2.py`)

> **Note:** There is also a legacy `SettingsBridge` (`ui_qml_bridge/settings_bridge.py`) that remains available but is superseded by `SettingsBridgeV2`. The legacy bridge uses inline `settings_manager` imports. `SettingsBridgeV2` uses `SettingsService` dependency injection. Both are documented here for completeness.

---

## SettingsBridgeV2 (Primary)

### Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `service` | `SettingsService \| None` | `SettingsService()` |
| `parent` | `QObject \| None` | `None` |

### Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `categories` | `QVariantList` | `dataChanged` | List of setting category dicts |

### Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `getValue` | `key: str` | `QVariant` | Get a setting value |
| `setValue` | `key: str, value: QVariant` | `dict` | Set a setting value |
| `resetValue` | `key: str` | `dict` | Reset a single setting to default |
| `resetAll` | — | `dict` | Reset all settings to defaults |
| `refresh` | — | `void` | Emit dataChanged |

### Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Setting data changed |

---

## SettingsBridge (Legacy)

### Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `parent` | `QObject \| None` | `None` |

### Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `sections` | `QVariantList` | `settingsChanged` | 8 hardcoded setting sections (general, appearance, library, playback, audio, michi_link, privacy, experimental) |
| `outputProfiles` | `QVariantList` | `settingsChanged` | Audio output profiles from audio/output_profiles.py |

### Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `void` | Emit settingsChanged |
| `getActiveProfile` | — | `str` | Get current audio profile from settings |
| `setActiveProfile` | `key: str` | `dict` | Set audio profile |
| `get` | `key: str` | `str` | Get setting value as string |
| `set` | `key: str, value: str` | `void` | Set setting value |

### Signals
| Name | Payload | Description |
|------|---------|-------------|
| `settingsChanged` | — | Settings changed |

## Integration
- **JobService**: Not used
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Not registered as a capability; always available

## Cancellation Contract
- None. Setting operations are synchronous and immediate.

## Destructive Action Handling
- `resetAll()` — irreversible; resets all settings to defaults
- `resetValue(key)` — irreversible per-key reset
- No confirmation/undo

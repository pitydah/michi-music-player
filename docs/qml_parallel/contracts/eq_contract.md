# EQ Bridge Contract

## Context Property
`EqBridge` registered as `eq` context property.

## Class Name
`EqBridge` (`ui_qml_bridge/eq_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `player_service` | `Any (PlayerService) \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `enabled` | `bool` | `stateChanged` | Whether EQ is enabled |
| `bypass` | `bool` | `stateChanged` | Whether EQ is bypassed |
| `backendAvailable` | `bool` | `stateChanged` | Whether player supports EQ |
| `bitperfectConflict` | `bool` | `stateChanged` | True when MPD backend blocks EQ |
| `presets` | `QVariantList` | `stateChanged` | List of preset dicts with name, bands |
| `currentPreset` | `str` | `stateChanged` | Name of active preset |
| `preamp` | `float` | `stateChanged` | Preamp gain in dB |
| `graphicBands` | `QVariantList` | `stateChanged` | 10 graphic band dicts with freq, gain |
| `parametricBands` | `QVariantList` | `stateChanged` | 6 parametric band dicts with freq, gain, q, type, enabled |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `refresh` | — | `dict` | Load presets and update backend state |
| `applyPreset` | `name: str` | `dict` | Apply a graphic EQ preset |
| `setEnabled` | `enabled: bool` | `dict` | Enable/disable EQ (delegates to toggleBypass) |
| `toggleBypass` | `enabled: bool` | `dict` | Set bypass state |
| `setPreamp` | `value: float` | `dict` | Set preamp gain |
| `setGraphicBand` | `index: int, gain: float` | `dict` | Set a single graphic band gain (clamped -24 to +24 dB) |
| `setParametricBand` | `index: int, band_type: str, freq: float, gain: float, enabled: bool` | `dict` | Set a single parametric band |
| `reset` | — | `dict` | Reset all bands to 0, preamp to 0, bypass off |
| `importPreset` | `filepath: str` | `dict` | Import a JSON preset file |
| `exportPreset` | `filepath: str` | `dict` | Export current settings as JSON |
| `saveState` | — | `dict` | Persist current EQ state to settings |
| `saveCustomPreset` | `name: str` | `dict` | Save current graphic bands as custom preset |
| `restoreState` | — | `dict` | Load EQ state from saved settings |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `stateChanged` | — | Any EQ property changed |

## Models Exposed
None. Bands returned as QVariantList.

## Constants
- `GRAPHIC_BAND_COUNT = 10`
- `PARAMETRIC_BAND_COUNT = 6`
- `DEFAULT_GRAPHIC_FREQS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]`

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"NO_PLAYER"`, `"BITPERFECT_CONFLICT"`, `"FAILED_TO_APPLY"`, `"INVALID_INDEX"`, `"EMPTY_NAME"`, `"FILE_NOT_FOUND"`, `"INVALID_BAND_COUNT"`

## Error Codes
- `NO_PLAYER` — player_service is None
- `BITPERFECT_CONFLICT` — MPD backend active, EQ blocked
- `FAILED_TO_APPLY` — preset bands not loaded
- `INVALID_INDEX` — band index out of range
- `EMPTY_NAME` — empty preset name
- `FILE_NOT_FOUND` — import file doesn't exist
- `INVALID_BAND_COUNT` — import file has wrong band count

## States
- `_backend_available`: derived from `player.has_eq_state`
- `_bitperfect_conflict`: set when active backend contains "mpd"
- All band gains clamped to [-24, +24] dB

## Lifecycle
- Created by `BridgeFactory.create_eq_bridge()` with player_service
- `player_service` may be None (factory returns None if no player_service)
- `refresh()` loads presets from `audio.eq_presets` module and updates backend state
- `restoreState()` restores from `settings_manager` (persistent across sessions)

## Behavior When Service Is Null/Missing
- Without `player_service`: `backendAvailable` = False, all player-dependent operations return `"NO_PLAYER"`
- Preset loading still works (read-only EQ interface)
- Import/export/save custom preset still works

## Integration
- **JobService**: Not used
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `eq` capability; requires `player_service`

## Cancellation Contract
- None. EQ operations are synchronous.

## Destructive Action Handling
- `reset()` clears all bands and settings (reversible via `restoreState()` or re-applying preset)
- `saveState()` overwrites saved EQ state
- `saveCustomPreset()` overwrites custom presets

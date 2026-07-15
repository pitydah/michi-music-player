# Global Search Bridge Contract

## Context Property
`GlobalSearchBridge` registered as `global_search` context property.

## Class Name
`GlobalSearchBridge` (`ui_qml_bridge/global_search_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `search_service` | `Any (SearchService) \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `query` | `str` | `resultsChanged` | Current search query text |
| `results` | `QVariantList` | `resultsChanged` | Search results (max 50 items) |
| `isSearching` | `bool` | `searchingChanged` | Whether a search is in progress |
| `errorCode` | `str` | `resultsChanged` | Last error code |
| `errorMessage` | `str` | `resultsChanged` | Last error message |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `search` | `query: str` | `dict` | Execute search; stale-result-safe via request counter |
| `cancel` | — | `dict` | Cancel active search; clear results |
| `searchDomain` | `domain: str, query: str` | `dict` | Scoped search within a domain prefix |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `resultsChanged` | — | Results, query, error state changed |
| `searchingChanged` | — | isSearching flag changed |

## Models Exposed
None. Results returned as `QVariantList` of dicts.

## DOMAIN_MAP
track, album, artist, playlist, folder, genre, device, server, action, setting

## Error Handling
- Error codes: `"SEARCH_FAILED"`, `"SERVICE_UNAVAILABLE"`, `"UNKNOWN_DOMAIN"`
- Callback pattern: `_on_done(result)` processes async result
- Stale request detection via `_active_request_id` counter

## Error Codes
- `SEARCH_FAILED` — search service returned error or exception
- `SERVICE_UNAVAILABLE` — no search service injected
- `UNKNOWN_DOMAIN` — domain not in DOMAIN_MAP

## States
- `isSearching`: true while search is in progress, false when done/cancelled
- `errorCode`, `errorMessage`: cleared on new search, set on failure

## Lifecycle
- Created by `BridgeFactory.create_global_search_bridge()` with search_service=None
- Auto-cancels stale searches via request ID counter
- No background polling; QML initiates searches

## Behavior When Service Is Null/Missing
- Without `search_service`: all searches return `{"ok": false, "error": "SERVICE_UNAVAILABLE"}`
- Results remain empty

## Integration
- **JobService**: Not used
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `global_search` capability (via `has_fts5` check)

## Cancellation Contract
- `cancel()` sets `_active_request_id = 0` (invalidates all pending callbacks)
- Calls `_svc.cancel(owner="global_search")` if available
- Stale results from previous requests are discarded by comparing request IDs

## Destructive Action Handling
- None. Search is read-only.

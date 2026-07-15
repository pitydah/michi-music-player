<<<<<<< Updated upstream
# GlobalSearchBridge Integration Contract
=======
<<<<<<< HEAD
# Global Search Bridge Contract
>>>>>>> Stashed changes

## Context Property
- `globalSearchBridge` → `GlobalSearchBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `query` | `str` | `resultsChanged` |
| `results` | `QVariantList` | `resultsChanged` |
| `isSearching` | `bool` | `searchingChanged` |
| `errorCode` | `str` | `resultsChanged` |
| `errorMessage` | `str` | `resultsChanged` |

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `search` | `dict` | `query: str` |
| `cancel` | `dict` | none |
| `searchDomain` | `dict` | `domain: str`, `query: str` |

All slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `resultsChanged` | (none) |
| `searchingChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"SEARCH_FAILED"` — search service returned error
- `"SERVICE_UNAVAILABLE"` — no SearchService injected
- `"UNKNOWN_DOMAIN"` — domain not in `DOMAIN_MAP`

## DOMAIN_MAP
`track`, `album`, `artist`, `playlist`, `folder`, `genre`, `device`, `server`, `action`, `setting`.

## Lifecycle Expectations
- Constructor takes optional `search_service`.
- `search(query)`: increments `_request_counter`, sets `_active_request_id` for stale-guard.
- Empty query clears results immediately.
- Results capped at `_MAX_TOTAL = 50`.
- Search service called with `owner="global_search"`, `timeout_ms=5000`.

## Stale Result Guard
- `_active_request_id` is checked in `_on_done` callback; stale responses discarded.

## Behavior When Service Is Missing/Null
- No `_svc` or `_svc.search` not callable: returns `SERVICE_UNAVAILABLE` with Spanish error message.

## Destructive Actions and Confirmations
None — read-only search.

## Cancellation Contract
- `cancel()`: sets `_active_request_id = 0` (invalidates all pending callbacks), calls `_svc.cancel(owner="global_search")` if available. Clears results and sets `isSearching=False`. Increments `_search_gen`.

<<<<<<< Updated upstream
=======
## Destructive Action Handling
- None. Search is read-only.
=======
# GlobalSearchBridge Integration Contract

## Context Property
- `globalSearchBridge` → `GlobalSearchBridge` instance

## Properties
| Property | Type | Notify Signal |
|---|---|---|
| `query` | `str` | `resultsChanged` |
| `results` | `QVariantList` | `resultsChanged` |
| `isSearching` | `bool` | `searchingChanged` |
| `errorCode` | `str` | `resultsChanged` |
| `errorMessage` | `str` | `resultsChanged` |

## Slots
| Slot | Returns | Parameters |
|---|---|---|
| `search` | `dict` | `query: str` |
| `cancel` | `dict` | none |
| `searchDomain` | `dict` | `domain: str`, `query: str` |

All slots return `dict` with `ok: bool`.

## Signals
| Signal | Payload |
|---|---|
| `resultsChanged` | (none) |
| `searchingChanged` | (none) |

## Models Exposed
None.

## Error Types/Codes
- `"SEARCH_FAILED"` — search service returned error
- `"SERVICE_UNAVAILABLE"` — no SearchService injected
- `"UNKNOWN_DOMAIN"` — domain not in `DOMAIN_MAP`

## DOMAIN_MAP
`track`, `album`, `artist`, `playlist`, `folder`, `genre`, `device`, `server`, `action`, `setting`.

## Lifecycle Expectations
- Constructor takes optional `search_service`.
- `search(query)`: increments `_request_counter`, sets `_active_request_id` for stale-guard.
- Empty query clears results immediately.
- Results capped at `_MAX_TOTAL = 50`.
- Search service called with `owner="global_search"`, `timeout_ms=5000`.

## Stale Result Guard
- `_active_request_id` is checked in `_on_done` callback; stale responses discarded.

## Behavior When Service Is Missing/Null
- No `_svc` or `_svc.search` not callable: returns `SERVICE_UNAVAILABLE` with Spanish error message.

## Destructive Actions and Confirmations
None — read-only search.

## Cancellation Contract
- `cancel()`: sets `_active_request_id = 0` (invalidates all pending callbacks), calls `_svc.cancel(owner="global_search")` if available. Clears results and sets `isSearching=False`. Increments `_search_gen`.

>>>>>>> Stashed changes
## Integration with JobService
NOT IMPLEMENTED — search is synchronous (blocking) with no WorkerManager integration.

## Integration with ActionRegistry
NOT IMPLEMENTED.

## Integration with NavigationBridge
NOT IMPLEMENTED.

## Integration with PageStateStore
NOT IMPLEMENTED.

## Integration with CapabilityBridge
NOT IMPLEMENTED.

## Integration with AccessibilityBridge
NOT IMPLEMENTED.
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

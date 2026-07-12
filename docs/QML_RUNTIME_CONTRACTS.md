# QML Runtime Contracts

## Signal delivery

All cross-thread signals use `Qt.ConnectionType.QueuedConnection`.
No QObject signals emitted from QRunnable.

## WorkerManager → QueryExecutor → Model

```
WorkerManager.run_task(task_id, fn, on_done, on_error)
  → _TaskWorker (QRunnable, no QObject children)
    → done_callback/error_callback (called from worker thread)
      → task_done/task_error signals (QueuedConnection to main thread)
        → QueryExecutor._on_task_done
          → success/failure signals (main thread)
            → BasePagedListModel._on_success/_on_error
              → beginResetModel/beginInsertRows (main thread only)
```

## Error codes

| Code | Source | Description |
|---|---|---|
| QUERY_FAILED | QueryExecutor | Generic query error |
| QUERY_CANCELLED | QueryExecutor | Cancelled by user/owner |
| QUERY_STALE | QueryExecutor | Superseded by newer query |
| SQLITE_BUSY | QueryExecutor | Database locked |
| SQLITE_THREAD_ERROR | QueryExecutor | Wrong thread access |
| NO_DB | LibraryQueryService | Database not available |
| NOT_FOUND | LibraryQueryService | Track/album/artist not found |
| FILE_NOT_FOUND | LibraryBridge | File does not exist on disk |
| NO_PLAYER_SERVICE | LibraryBridge | Player not available |
| NO_HANDLER | ActionRegistry | Action has no handler bound |
| UNSUPPORTED | Multiple | Feature not available |
| DIR_NOT_FOUND | LibrarySourcesService | Directory does not exist |
| ALREADY_EXISTS | LibrarySourcesService | Duplicate source |

## Owner IDs

| Owner | Used by |
|---|---|
| `tracks` | TrackListModel |
| `albums` | AlbumListModel |
| `artists` | ArtistListModel |
| `folders` | FolderTreeModel |
| `queue` | QueueListModel |
| `history` | HistoryListModel |
| `jobs` | JobBridge |
| `smart_tagging` | SmartTaggingBridge |

## Generation protocol

Each owner has a generation counter in QueryExecutor.
When a new request supersedes, the generation increments.
Callbacks check generation before modifying models.
Stale callbacks are silently dropped.
